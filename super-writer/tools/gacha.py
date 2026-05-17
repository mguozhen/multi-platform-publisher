#!/usr/bin/env python3
"""
内容抽卡器 — aggregates 5 sources, scores, draws 3 topic cards.

USAGE
  python3 gacha.py --draw                 draw 3 cards, save to content/cards/
  python3 gacha.py --draw --dry-run       draw + print, don't save
  python3 gacha.py --draw --push          draw + push to Telegram via the bridge
  python3 gacha.py --show [DATE]          show a saved day's cards

SCORING (rule-based v1)
  base 0.5
  + freshness   (linear decay over 7 days, max +0.3)
  + inbox boost (+0.2 — Hunter fed it in)
  + platform-spread / source-diversity handled at draw time (pick 3 distinct)

OUTPUT  content/cards/YYYY-MM-DD.json — array of card dicts:
  {id, kind:"topic", title, source, source_ref, rationale,
   suggested_platforms, score, status:"drawn"}
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
SELF_MEDIA = HERE.parent
CARDS_DIR = SELF_MEDIA / "content" / "cards"
sys.path.insert(0, str(HERE))

from sources import github_source, session_source, inbox_source, gtm_source, wechat_source  # noqa: E402

SOURCES = {
    "github": github_source,
    "session": session_source,
    "inbox": inbox_source,
    "gtm": gtm_source,
    "wechat": wechat_source,
}


# ──────────────────────── aggregate ─────────────────────────
def aggregate() -> list[dict]:
    """Collect from all 5 sources. Failures isolated per-source."""
    all_cands: list[dict] = []
    for name, mod in SOURCES.items():
        try:
            cands = mod.collect()
            all_cands.extend(cands)
            print(f"  [{name}] {len(cands)} candidates")
        except Exception as e:  # noqa: BLE001
            print(f"  [{name}] FAILED: {e}")
    return all_cands


# ──────────────────────── score ─────────────────────────────
def score(cand: dict) -> float:
    s = 0.5
    # freshness — linear decay over 7 days
    age_days = (time.time() - cand.get("raw_ts", time.time())) / 86400
    s += max(0.0, 0.3 * (1 - age_days / 7))
    # inbox boost
    if cand.get("source") == "inbox":
        s += 0.2
    return round(min(s, 1.0), 3)


# ──────────────────────── 中文化 ─────────────────────────
def _load_env() -> None:
    env_file = HERE / "telegram-bridge" / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def localize(cards: list[dict]) -> list[dict]:
    """把卡片 title / rationale 统一改写成中文选题。一次 LLM 调用处理全部。"""
    _load_env()
    try:
        from openai import OpenAI
    except ImportError:
        print("  [localize] 无 openai SDK，跳过")
        return cards
    key = os.environ.get("LLM_API_KEY", "")
    if not key:
        print("  [localize] 无 LLM_API_KEY，跳过")
        return cards
    items = "\n".join(
        f"{i}. 标题: {c['title']}\n   理由: {c.get('rationale', '')}"
        for i, c in enumerate(cards))
    prompt = (
        "把下面这些自媒体选题卡改写成中文。每张卡给一个中文标题"
        "（一句话选题，不超过 30 字，口语、有钩子）和一句中文理由。"
        "已经是中文的也润色一下。\n\n"
        f"{items}\n\n"
        '只返回 JSON 数组，格式 [{"title":"…","rationale":"…"}]，'
        "顺序与输入对应，不要任何别的文字。")
    try:
        client = OpenAI(base_url=os.environ.get("LLM_BASE_URL",
                        "https://api.flatkey.ai/v1"), api_key=key)
        resp = client.chat.completions.create(
            model=os.environ.get("LLM_MODEL", "gpt-5-mini"),
            messages=[{"role": "user", "content": prompt}], max_tokens=900)
        out = (resp.choices[0].message.content or "").strip()
        if out.startswith("```"):
            out = out.split("```")[1]
            out = out[4:] if out.startswith("json") else out
        data = json.loads(out.strip())
        for c, z in zip(cards, data):
            if z.get("title"):
                c["title"] = z["title"].strip()
            if z.get("rationale"):
                c["rationale"] = z["rationale"].strip()
        print(f"  [localize] {len(data)} 张卡已中文化")
    except Exception as e:  # noqa: BLE001
        print(f"  [localize] 失败，保留原文: {e}")
    return cards


# ──────────────────────── draw ──────────────────────────────
def draw(n: int = 3) -> list[dict]:
    """Aggregate → score → pick n with source diversity."""
    cands = aggregate()
    if not cands:
        return []
    for c in cands:
        c["score"] = score(c)
    cands.sort(key=lambda c: c["score"], reverse=True)

    # source-diversity: prefer not repeating a source until all are used
    picked: list[dict] = []
    used_sources: set[str] = set()
    pool = list(cands)
    while pool and len(picked) < n:
        choice = None
        for c in pool:
            if c["source"] not in used_sources:
                choice = c
                break
        if choice is None:           # all sources used — take highest remaining
            choice = pool[0]
        picked.append(choice)
        used_sources.add(choice["source"])
        pool.remove(choice)

    # finalize cards
    cards = []
    for c in picked:
        cards.append({
            "id": secrets.token_hex(3),
            "kind": "topic",
            "title": c["title"],
            "source": c["source"],
            "source_ref": c.get("source_ref", ""),
            "rationale": c.get("rationale", ""),
            "suggested_platforms": c.get("suggested_platforms", ["x"]),
            "score": c["score"],
            "status": "drawn",
            "_inbox_file": c.get("_inbox_file"),
            "_full_content": c.get("_full_content"),
        })
    return localize(cards)


# ──────────────────────── persist ───────────────────────────
def save_cards(cards: list[dict]) -> Path:
    CARDS_DIR.mkdir(parents=True, exist_ok=True)
    f = CARDS_DIR / f"{date.today().isoformat()}.json"
    f.write_text(json.dumps(cards, ensure_ascii=False, indent=2), encoding="utf-8")
    # move drawn inbox files to _used/
    used_dir = SELF_MEDIA / "inbox" / "_used"
    for c in cards:
        ib = c.get("_inbox_file")
        if ib and Path(ib).exists():
            used_dir.mkdir(exist_ok=True)
            Path(ib).rename(used_dir / Path(ib).name)
    return f


def push_to_telegram(cards: list[dict]) -> None:
    """Hand the cards to the telegram bridge as a topic-batch."""
    bridge = HERE / "telegram-bridge" / "bridge.py"
    if not bridge.exists():
        print("  [push] bridge.py not found — skipping")
        return
    payload = json.dumps(cards, ensure_ascii=False)
    try:
        out = subprocess.run(
            ["python3", str(bridge), "--enqueue-cards", payload],
            capture_output=True, text=True, timeout=60,
        )
        print(out.stdout.strip() or out.stderr.strip())
    except Exception as e:  # noqa: BLE001
        print(f"  [push] failed: {e}")


# ──────────────────────── cli ───────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser(description="内容抽卡器")
    ap.add_argument("--draw", action="store_true", help="draw 3 topic cards")
    ap.add_argument("--dry-run", action="store_true", help="print, don't save")
    ap.add_argument("--push", action="store_true", help="push to Telegram bridge")
    ap.add_argument("--show", nargs="?", const=date.today().isoformat(),
                    help="show a saved day's cards")
    ap.add_argument("-n", type=int, default=3, help="number of cards")
    args = ap.parse_args()

    if args.show:
        f = CARDS_DIR / f"{args.show}.json"
        if not f.exists():
            sys.exit(f"no cards for {args.show}")
        for c in json.loads(f.read_text()):
            print(f"  🃏 {c['id']}  [{c['source']}·{c['score']}]  {c['title']}")
        return

    if args.draw:
        print("aggregating sources…")
        cards = draw(args.n)
        if not cards:
            print("no candidates found.")
            return
        print(f"\ndrew {len(cards)} cards:")
        for i, c in enumerate(cards, 1):
            print(f"  🃏 卡{i}  [{c['source']}·score {c['score']}]")
            print(f"      {c['title']}")
            print(f"      建议平台: {', '.join(c['suggested_platforms'])}")
        if args.dry_run:
            print("\n(dry-run — not saved)")
            return
        f = save_cards(cards)
        print(f"\n✅ saved → {f}")
        if args.push:
            push_to_telegram(cards)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()

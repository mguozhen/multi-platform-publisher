"""mpp service — Telegram 命令 /mpp <article> 触发的全平台发布。

流程:
  article.md
    │
    ├─ 每个平台:
    │    ├─ 读 ~/self-media/playbooks/<platform>.md
    │    ├─ Claude 按 playbook 改写 (claude_call.claude_adapt)
    │    └─ publish_router.publish() 实际发布
    │
    └─ 收集 {platform: {ok, url, note|error}} 返回

调用方式:
  from mpp.service import run_all
  results = run_all(article_text, platforms=["x","linkedin","devto","qiita","wechat"],
                    title="...", link="https://github.com/...", tags={"devto":["opensource"]})

CLI（手动测试用）:
  python3 -m mpp.service <article-path> --platforms x,linkedin,devto,qiita,wechat
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Callable

HOME = Path.home()
PLAYBOOKS = HOME / "self-media" / "playbooks"

sys.path.insert(0, str(Path(__file__).parent))  # for sibling imports
from claude_call import claude_adapt  # noqa: E402
import publish_router  # noqa: E402


def _load_playbook(platform: str) -> str:
    p = PLAYBOOKS / f"{platform}.md"
    if not p.exists():
        raise RuntimeError(f"playbook 缺失: {p}")
    return p.read_text(encoding="utf-8")


def run_one(platform: str, article: str, *, title: str | None = None,
            tags: list[str] | None = None, link: str | None = None,
            model: str = "sonnet") -> dict:
    """改写 + 发布一个平台。返回 {platform, ok, url|error, adapted, note}。"""
    out = {"platform": platform, "ok": False}
    try:
        playbook = _load_playbook(platform)
    except Exception as e:
        out["error"] = str(e)
        return out
    try:
        adapted = claude_adapt(article=article, playbook=playbook,
                               platform=platform, model=model)
    except Exception as e:
        out["error"] = f"adapt failed: {e}"
        return out
    out["adapted"] = adapted

    r = publish_router.publish(platform, adapted, title=title,
                               tags=tags, link=link)
    out.update(r)
    return out


def run_all(article: str, platforms: list[str], *,
            title: str | None = None,
            link: str | None = None,
            tags: dict | None = None,
            model: str = "sonnet",
            progress: Callable[[str, dict], None] | None = None) -> dict:
    """对一篇文章跑所有指定平台。progress 回调可挂 Telegram 实时反馈。"""
    tags = tags or {}
    results = {}
    for p in platforms:
        if progress:
            progress(p, {"status": "adapting"})
        r = run_one(p, article, title=title, link=link,
                    tags=tags.get(p, []), model=model)
        results[p] = r
        if progress:
            progress(p, r)
        # rate-limit between platforms
        time.sleep(1.5)
    return {"results": results,
            "summary": _summary(results)}


def _summary(results: dict) -> str:
    lines = []
    for p, r in results.items():
        if r.get("ok"):
            lines.append(f"✅ {p}: {r.get('url','')}")
        else:
            lines.append(f"❌ {p}: {r.get('error','?')[:120]}")
    return "\n".join(lines)


# ───────────────────────── CLI ─────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser(description="mpp service")
    ap.add_argument("article", help="path to article .md (first H1 = title)")
    ap.add_argument("--platforms", default="x,linkedin,devto,qiita,wechat",
                    help="comma-separated platforms")
    ap.add_argument("--link", default=None, help="canonical repo/landing link")
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--devto-tags", default="opensource,ai,productivity,showdev")
    ap.add_argument("--qiita-tags", default="OSS,AI,個人開発,AIエージェント")
    args = ap.parse_args()

    text = Path(args.article).expanduser().read_text(encoding="utf-8")
    # H1 as title
    m = re.search(r"^#\s+(.+)$", text, re.M)
    title = m.group(1).strip() if m else None

    tags = {"devto": [t.strip() for t in args.devto_tags.split(",")],
            "qiita": [t.strip() for t in args.qiita_tags.split(",")]}

    def cli_progress(plat: str, r: dict) -> None:
        status = r.get("status") or ("ok" if r.get("ok") else "error")
        print(f"[{plat}] {status} {r.get('url') or r.get('error') or ''}",
              file=sys.stderr)

    out = run_all(text, args.platforms.split(","),
                  title=title, link=args.link, tags=tags,
                  model=args.model, progress=cli_progress)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

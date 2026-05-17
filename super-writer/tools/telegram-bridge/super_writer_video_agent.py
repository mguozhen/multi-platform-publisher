#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


BRIDGE = Path("/Users/hunter/self-media/tools/telegram-bridge")
AUTOPOST = Path("/Users/hunter/autopost.video")
VOC_OUT = AUTOPOST / "outputs" / "voc_amazon_review_skill"


def latest_voc_batch() -> dict | None:
    queue = BRIDGE / "queue.json"
    if not queue.exists():
        return None
    q = json.loads(queue.read_text(encoding="utf-8") or "[]")
    batches = [
        e for e in q
        if e.get("kind") == "topic_batch"
        and any(c.get("source") == "voc-review-skill" for c in e.get("cards", []))
    ]
    return batches[-1] if batches else None


def render_voc(card_index: int | None = None) -> Path:
    batch = latest_voc_batch()
    if batch and card_index is None:
        picked = batch.get("picked_idx")
        card_index = int(picked) + 1 if picked is not None else 1
    card_index = card_index or 1
    if card_index != 1:
        print(f"[agent] card {card_index} requested; renderer currently uses card 1 visual/script.")
    script = VOC_OUT / "render_voc_review_financial_style.py"
    subprocess.run(
        ["python3", str(script)],
        cwd=AUTOPOST,
        check=True,
    )
    return VOC_OUT / "voc_amazon_review_financial_style_9x16_fixed.mp4"


def main() -> int:
    ap = argparse.ArgumentParser(description="Super-writer video generation agent for autopost.video")
    ap.add_argument("--task", choices=["voc-amazon-review"], default="voc-amazon-review")
    ap.add_argument("--card", type=int, default=None)
    ap.add_argument("--open", action="store_true")
    args = ap.parse_args()

    if args.task == "voc-amazon-review":
        out = render_voc(args.card)
    else:
        raise SystemExit(f"unsupported task: {args.task}")

    print(out)
    if args.open:
        subprocess.run(["open", str(out)], check=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""
WeChat source — Hunter's own published 公众号 articles as a topic well.

A published article can seed: a follow-up, a cross-platform repurpose,
or a "X 后续" angle. Reads a local index file (no scraping — WeChat
blocks anonymous access).

Maintain the index at ~/self-media/content/wechat-published.json:
  [{"title": "...", "url": "...", "date": "2026-05-14"}, ...]

collect() -> list[dict]
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

INDEX = Path.home() / "self-media" / "content" / "wechat-published.json"


def collect(days: int = 30) -> list[dict]:
    if not INDEX.exists():
        return []
    try:
        articles = json.loads(INDEX.read_text(encoding="utf-8") or "[]")
    except json.JSONDecodeError:
        return []

    cutoff = time.time() - days * 86400
    cands: list[dict] = []

    for a in articles:
        title = a.get("title", "")
        if not title:
            continue
        date = a.get("date", "")
        ts = time.time()
        if date:
            try:
                ts = datetime.fromisoformat(date).timestamp()
            except ValueError:
                pass
        if ts < cutoff:
            continue
        cands.append({
            "title": f"跨平台复用 / 后续: {title}",
            "source": "wechat",
            "source_ref": a.get("url", ""),
            "rationale": f"已发公众号文章「{title}」— 可做 X/小红书 复用 或后续追踪",
            "suggested_platforms": ["x", "xiaohongshu"],
            "raw_ts": ts,
        })

    return cands


if __name__ == "__main__":
    cs = collect()
    for c in cs:
        print(f"  [{c['source']}] {c['title']}")
    print(f"({len(cs)} candidates)")

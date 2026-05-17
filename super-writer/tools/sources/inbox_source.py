"""
Inbox source — Hunter's manually-fed content ideas.

Reads ~/self-media/inbox/*.{txt,md,url}. Each file = one topic candidate.
Inbox candidates carry a +0.2 score weight (handled in gacha.py).
collect() -> list[dict]
"""
from __future__ import annotations

import time
from pathlib import Path

INBOX = Path.home() / "self-media" / "inbox"


def collect() -> list[dict]:
    if not INBOX.is_dir():
        return []
    cands: list[dict] = []

    for f in sorted(INBOX.iterdir()):
        if f.is_dir() or f.name.startswith(".") or f.name == "README.md":
            continue
        if f.suffix not in (".txt", ".md", ".url"):
            continue
        try:
            content = f.read_text(encoding="utf-8", errors="replace").strip()
        except Exception:  # noqa: BLE001
            continue
        if not content:
            continue
        # first line / first 80 chars as the title
        first = content.splitlines()[0].strip()
        title = first[:80] if first else f.stem
        cands.append({
            "title": title,
            "source": "inbox",
            "source_ref": str(f),
            "rationale": "Hunter fed this in manually — highest-priority signal",
            "suggested_platforms": ["x", "wechat", "xiaohongshu"],
            "raw_ts": f.stat().st_mtime,
            "_inbox_file": str(f),       # gacha moves this to _used/ after drawing
            "_full_content": content,
        })

    return cands


if __name__ == "__main__":
    cs = collect()
    for c in cs:
        print(f"  [{c['source']}] {c['title']}")
    print(f"({len(cs)} candidates)")

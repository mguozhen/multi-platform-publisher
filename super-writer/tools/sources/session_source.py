"""
Session source — recent local project activity.

Scans ~/ for git repos with commits in the last N days.
Each active project becomes a topic candidate.
collect() -> list[dict]
"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

HOME = Path.home()

# Projects worth surfacing as content (skip noise)
WATCH = [
    "self-media", "todo-eleven", "wx-schedule", "flatkey", "autopost.video",
    "agent-teams", "ai-crypto-claw", "kbeauty.ai", "arxify", "cnapi",
    "gtm-swarm", "mguozhen",
]


def _recent_commits(repo: Path, days: int) -> list[str]:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "log", f"--since={days}.days.ago",
             "--pretty=%s", "--no-merges"],
            capture_output=True, text=True, timeout=15,
        )
    except Exception:  # noqa: BLE001
        return []
    if out.returncode != 0:
        return []
    return [ln for ln in out.stdout.splitlines() if ln.strip()]


def collect(days: int = 7) -> list[dict]:
    cands: list[dict] = []
    now = time.time()

    for name in WATCH:
        repo = HOME / name
        if not (repo / ".git").is_dir():
            continue
        commits = _recent_commits(repo, days)
        if not commits:
            continue
        # most recent commit subject is the headline
        headline = commits[0]
        cands.append({
            "title": f"{name}: {headline}",
            "source": "session",
            "source_ref": str(repo),
            "rationale": f"{len(commits)} commits in {name} within {days}d — active build worth a post",
            "suggested_platforms": ["x", "douyin"],
            "raw_ts": now,  # local activity treated as fresh
        })

    return cands


if __name__ == "__main__":
    cs = collect()
    for c in cs:
        print(f"  [{c['source']}] {c['title']}")
    print(f"({len(cs)} candidates)")

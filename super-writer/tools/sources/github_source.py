"""
GitHub source — recent repo activity from github.com/mguozhen.

Each repo pushed in the last 7 days becomes a topic candidate.
collect() -> list[dict]
"""
from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timezone


def collect(days: int = 7) -> list[dict]:
    try:
        out = subprocess.run(
            ["gh", "repo", "list", "mguozhen", "--limit", "100",
             "--json", "name,description,pushedAt,url,isFork"],
            capture_output=True, text=True, timeout=30,
        )
    except Exception as e:  # noqa: BLE001
        print(f"[github_source] gh failed: {e}")
        return []
    if out.returncode != 0:
        print(f"[github_source] gh error: {out.stderr.strip()}")
        return []

    repos = json.loads(out.stdout or "[]")
    cutoff = time.time() - days * 86400
    cands: list[dict] = []

    for r in repos:
        if r.get("isFork"):
            continue
        pushed = r.get("pushedAt", "")
        if not pushed:
            continue
        try:
            ts = datetime.fromisoformat(pushed.replace("Z", "+00:00")).timestamp()
        except ValueError:
            continue
        if ts < cutoff:
            continue
        name = r["name"]
        desc = r.get("description") or ""
        cands.append({
            "title": f"{name} — {desc}" if desc else f"shipped: {name}",
            "source": "github",
            "source_ref": r.get("url", ""),
            "rationale": f"GitHub repo {name} pushed within {days}d — a real ship to talk about",
            "suggested_platforms": ["x", "wechat"],
            "raw_ts": ts,
        })

    return cands


if __name__ == "__main__":
    for c in collect():
        print(f"  [{c['source']}] {c['title']}")
    print(f"({len(collect())} candidates)")

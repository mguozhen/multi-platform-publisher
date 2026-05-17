"""
GTM swarm source — pulls topic ideas from the gtm-swarm idea pool.

Uses ~/gtm-swarm/bin/gtm-idea peek (local filesystem, JSON output).
collect() -> list[dict]
"""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

GTM_IDEA = Path.home() / "gtm-swarm" / "bin" / "gtm-idea.js"
PROJECTS = ["flatkey", "voc-ai", "voc"]


def _peek(project: str, limit: int = 5) -> list[dict]:
    if not GTM_IDEA.exists():
        return []
    try:
        out = subprocess.run(
            ["node", str(GTM_IDEA), "peek", "--project", project,
             "--limit", str(limit)],
            capture_output=True, text=True, timeout=20,
        )
    except Exception:  # noqa: BLE001
        return []
    if out.returncode != 0:
        return []
    try:
        data = json.loads(out.stdout or "[]")
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else data.get("ideas", [])


def collect() -> list[dict]:
    cands: list[dict] = []
    now = time.time()

    for project in PROJECTS:
        for idea in _peek(project):
            topic = idea.get("topic") or idea.get("title") or ""
            if not topic:
                continue
            hook = idea.get("suggested_hook", "")
            cands.append({
                "title": topic[:120],
                "source": "gtm",
                "source_ref": f"gtm-swarm/{project}",
                "rationale": f"GTM swarm idea for {project}" + (f" · hook: {hook}" if hook else ""),
                "suggested_platforms": ["x", "linkedin"],
                "raw_ts": now,
            })

    return cands


if __name__ == "__main__":
    cs = collect()
    for c in cs:
        print(f"  [{c['source']}] {c['title']}")
    print(f"({len(cs)} candidates)")

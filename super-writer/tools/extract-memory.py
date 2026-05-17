#!/usr/bin/env python3
"""
Hermes state.db → self-media persona archive extractor.

Reads a hermes state.db (sessions + messages), dumps a digestible
markdown corpus that Claude can then refine into 4 archive files:
  - hunter-profile.md
  - decisions-log.md
  - voice-samples.md
  - preferences.md

Usage:
  python3 extract-memory.py ~/self-media/memory/_import/hermes-state.db

Output:
  ~/self-media/memory/_import/corpus.md   (raw, for Claude to read)
  Then Claude reads corpus.md and writes the 4 archive files.
"""
import sqlite3
import sys
import datetime
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        db_path = Path.home() / "self-media/memory/_import/hermes-state.db"
    else:
        db_path = Path(sys.argv[1]).expanduser()

    if not db_path.exists():
        print(f"ERROR: {db_path} not found.", file=sys.stderr)
        print("scp the other machine's ~/.hermes/state.db here first.", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    sessions = conn.execute("SELECT * FROM sessions ORDER BY rowid").fetchall()
    msg_count = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]

    print(f"sessions: {len(sessions)}")
    print(f"messages: {msg_count}")

    out = Path.home() / "self-media/memory/_import/corpus.md"
    lines = []
    lines.append(f"# Hermes Memory Corpus")
    lines.append(f"> extracted {datetime.date.today()} from {db_path.name}")
    lines.append(f"> {len(sessions)} sessions / {msg_count} messages")
    lines.append("")

    for s in sessions:
        sid = s["id"]
        msgs = conn.execute(
            "SELECT role, content, tool_name, timestamp FROM messages "
            "WHERE session_id=? ORDER BY timestamp",
            (sid,),
        ).fetchall()
        # Skip empty / tool-only sessions
        human_msgs = [m for m in msgs if m["role"] in ("user", "assistant") and m["content"]]
        if not human_msgs:
            continue
        lines.append(f"## Session {sid}")
        for m in human_msgs:
            role = m["role"]
            content = (m["content"] or "").strip()
            if not content:
                continue
            # Truncate very long assistant messages
            if role == "assistant" and len(content) > 600:
                content = content[:600] + " …[truncated]"
            lines.append(f"**{role}**: {content}")
        lines.append("")

    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"✅ corpus written: {out}  ({out.stat().st_size // 1024} KB)")
    print("")
    print("Next: tell Claude '记忆 corpus 好了', Claude reads corpus.md")
    print("and writes the 4 archive files into ~/self-media/memory/")

    conn.close()


if __name__ == "__main__":
    main()

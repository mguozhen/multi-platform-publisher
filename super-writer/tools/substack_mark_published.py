#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path

from substack_publish_helper import read_section, read_title


TRACKING = Path("/Users/hunter/self-media/tracking/substack-posts.csv")


def main() -> None:
    parser = argparse.ArgumentParser(description="Record a published Substack post URL.")
    parser.add_argument("article_dir", type=Path)
    parser.add_argument("--url", required=True)
    args = parser.parse_args()

    article_dir = args.article_dir.resolve()
    meta_path = article_dir / "meta.md"
    checklist_path = article_dir / "publish-checklist.md"
    if not meta_path.exists():
        raise SystemExit(f"Missing meta.md: {meta_path}")

    meta = meta_path.read_text(encoding="utf-8")
    title = read_title(meta)
    slug = read_section(meta, "Slug")
    now = datetime.now().isoformat(timespec="seconds")

    TRACKING.parent.mkdir(parents=True, exist_ok=True)
    write_header = not TRACKING.exists()
    with TRACKING.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["published_at", "title", "slug", "url", "article_dir"])
        if write_header:
            writer.writeheader()
        writer.writerow(
            {
                "published_at": now,
                "title": title,
                "slug": slug,
                "url": args.url,
                "article_dir": str(article_dir),
            }
        )

    if checklist_path.exists():
        checklist = checklist_path.read_text(encoding="utf-8")
        checklist = checklist.replace("TBD", args.url, 1) if "## Public URL" in checklist else checklist
        checklist_path.write_text(checklist, encoding="utf-8")

    print(f"Recorded: {args.url}")
    print(f"Tracking: {TRACKING}")


if __name__ == "__main__":
    main()

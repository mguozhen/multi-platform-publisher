#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path


REQUIRED = ["post.md", "meta.md", "note.md", "publish-checklist.md"]


def read_title(meta: str) -> str:
    return read_section(meta, "Primary Title")


def read_section(meta: str, heading: str) -> str:
    lines = meta.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == f"## {heading}":
            for next_line in lines[i + 1 :]:
                value = next_line.strip()
                if value.startswith("## "):
                    return ""
                if value:
                    return value
    return ""


def read_tags(meta: str) -> str:
    value = read_section(meta, "Tags")
    return re.sub(r"\s*,\s*", ", ", value)


def copy_to_clipboard(text: str) -> None:
    try:
        subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
    except subprocess.CalledProcessError:
        print("Warning: pbcopy failed in this shell. Content was not copied.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a Substack article package for manual publishing.")
    parser.add_argument("article_dir", type=Path)
    parser.add_argument("--copy", choices=["post", "title", "subtitle", "excerpt", "tags", "note"], default="post")
    parser.add_argument("--open", action="store_true", help="Open Substack in the default browser.")
    parser.add_argument("--print", action="store_true", help="Print the selected field after copying.")
    args = parser.parse_args()

    article_dir = args.article_dir.resolve()
    missing = [name for name in REQUIRED if not (article_dir / name).exists()]
    if missing:
        raise SystemExit(f"Missing files in {article_dir}: {', '.join(missing)}")

    post = (article_dir / "post.md").read_text(encoding="utf-8")
    meta = (article_dir / "meta.md").read_text(encoding="utf-8")
    note = (article_dir / "note.md").read_text(encoding="utf-8")
    title = read_title(meta)
    subtitle = read_section(meta, "Subtitle")
    excerpt = read_section(meta, "Excerpt")
    tags = read_tags(meta)

    payload = {
        "post": post,
        "title": title,
        "subtitle": subtitle,
        "excerpt": excerpt,
        "tags": tags,
        "note": note,
    }[args.copy]
    copy_to_clipboard(payload)

    if args.open:
        subprocess.run(["open", "https://substack.com/"], check=False)

    print(f"Article package: {article_dir}")
    print(f"Copied: {args.copy}")
    if title:
        print(f"Title: {title}")
    if args.print:
        print("\n---")
        print(payload)
        print("---")
    print("\nNext:")
    print("1. Open Substack writer dashboard.")
    print("2. Create a new text post.")
    print("3. Paste title, subtitle, body, and tags from this package.")
    print("4. Preview, then publish or schedule manually.")


if __name__ == "__main__":
    main()

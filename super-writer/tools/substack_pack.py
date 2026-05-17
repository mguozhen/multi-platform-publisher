#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path


ROOT = Path("/Users/hunter/self-media")
OUT_ROOT = ROOT / "content" / "substack"


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", text)
    text = text.strip("-")
    return text[:80] or "untitled"


def write_if_missing(path: Path, content: str) -> None:
    if path.exists():
        raise SystemExit(f"Refusing to overwrite existing file: {path}")
    path.write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a Substack-ready article package.")
    parser.add_argument("--idea", required=True, help="Raw article idea or working title.")
    parser.add_argument("--slug", help="Optional slug. Defaults to slugified idea.")
    parser.add_argument("--title", help="Optional title. Defaults to idea.")
    parser.add_argument("--context", action="append", default=[], help="Context path to inspect while drafting.")
    parser.add_argument("--out-root", type=Path, default=OUT_ROOT)
    args = parser.parse_args()

    date = datetime.now().strftime("%Y-%m-%d")
    slug = args.slug or slugify(args.title or args.idea)
    title = args.title or args.idea.strip()
    article_dir = args.out_root / f"{date}-{slug}"
    article_dir.mkdir(parents=True, exist_ok=False)

    context_lines = "\n".join(f"- `{Path(p).expanduser()}`" for p in args.context) or "- None supplied"

    write_if_missing(
        article_dir / "brief.md",
        f"""# Brief

## Raw Idea

{args.idea}

## Context Paths

{context_lines}

## Drafting Instruction

Write this as a Substack essay in Hunter's founder-builder voice:

- personal build story first
- concrete tools/projects/files
- no generic tutorial voice
- no course/ad CTA
- strong claim, practical evidence, quiet ending
""",
    )

    write_if_missing(
        article_dir / "meta.md",
        f"""# Metadata

## Primary Title

{title}

## Alternate Titles

- TBD
- TBD
- TBD

## Subtitle

TBD

## Slug

{slug}

## Tags

AI agents, Codex, Claude Code, founder notes

## Excerpt

TBD

## Distribution

- Substack Post: long-form article.
- Substack Note / X: use `note.md`.
""",
    )

    write_if_missing(
        article_dir / "post.md",
        f"""# {title}

<!-- Draft the Substack post here. Use brief.md as source of truth. -->
""",
    )

    write_if_missing(
        article_dir / "note.md",
        """TBD
""",
    )

    write_if_missing(
        article_dir / "publish-checklist.md",
        """# Publish Checklist

1. Run `substack_publish_helper.py <article_dir> --copy title`.
2. Paste title into Substack.
3. Run `--copy subtitle` and paste subtitle.
4. Run `--copy post` and paste body.
5. Add tags from `--copy tags`.
6. Preview desktop and mobile.
7. Publish or schedule manually.
8. Copy the public URL into this file.

## Public URL

TBD
""",
    )

    print(article_dir)


if __name__ == "__main__":
    main()

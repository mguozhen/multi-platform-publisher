#!/usr/bin/env python3
"""
LinkedIn post publisher (after OAuth token is set).

Usage:
  source ~/.secrets/linkedin.env
  python3 li-post.py "Your post content here"

  # or from stdin:
  echo "post content" | python3 li-post.py

  # with image:
  python3 li-post.py "post content" --image /path/to/img.png
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import requests

ACCESS_TOKEN = os.environ.get("LINKEDIN_ACCESS_TOKEN", "")
PERSON_URN = os.environ.get("LINKEDIN_PERSON_URN", "")

if not ACCESS_TOKEN or not PERSON_URN:
    print("ERROR: Set LINKEDIN_ACCESS_TOKEN + LINKEDIN_PERSON_URN.", file=sys.stderr)
    print("Run: source ~/.secrets/linkedin.env", file=sys.stderr)
    sys.exit(1)

API_BASE = "https://api.linkedin.com"
HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "X-Restli-Protocol-Version": "2.0.0",
    "LinkedIn-Version": "202604",
    "Content-Type": "application/json",
}


def upload_image(path: Path) -> str:
    init = requests.post(
        f"{API_BASE}/rest/images?action=initializeUpload",
        headers=HEADERS,
        json={"initializeUploadRequest": {"owner": PERSON_URN}},
        timeout=30,
    )
    init.raise_for_status()
    data = init.json()["value"]
    upload_url = data["uploadUrl"]
    image_urn = data["image"]

    with open(path, "rb") as f:
        put = requests.put(upload_url, data=f.read(), timeout=60)
    put.raise_for_status()
    return image_urn


def publish_post(text: str, image_urn: str | None = None) -> dict:
    payload = {
        "author": PERSON_URN,
        "commentary": text,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    if image_urn:
        payload["content"] = {"media": {"id": image_urn, "title": ""}}
    r = requests.post(
        f"{API_BASE}/rest/posts",
        headers=HEADERS,
        json=payload,
        timeout=30,
    )
    if r.status_code >= 400:
        print(f"ERROR {r.status_code}: {r.text}", file=sys.stderr)
        r.raise_for_status()
    post_id = r.headers.get("x-restli-id") or r.headers.get("X-RestLi-Id", "")
    return {
        "id": post_id,
        "url": f"https://www.linkedin.com/feed/update/{post_id}" if post_id else None,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("text", nargs="?", help="Post text (or use stdin)")
    parser.add_argument("--image", help="Optional image path")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    text = args.text
    if not text and not sys.stdin.isatty():
        text = sys.stdin.read().strip()
    if not text:
        print("ERROR: no post content", file=sys.stderr)
        sys.exit(1)

    if len(text) > 3000:
        print(f"WARNING: post is {len(text)} chars (LinkedIn limit 3000)", file=sys.stderr)

    print(f"Publishing to LinkedIn ({len(text)} chars)...")
    print("---")
    print(text[:400] + ("..." if len(text) > 400 else ""))
    print("---")

    if args.dry_run:
        print("(dry-run; not actually posting)")
        return

    image_urn = None
    if args.image:
        img_path = Path(args.image).expanduser()
        print(f"Uploading image: {img_path}")
        image_urn = upload_image(img_path)
        print(f"  ✅ Image URN: {image_urn}")

    result = publish_post(text, image_urn)
    print(f"✅ Posted!")
    if result.get("url"):
        print(f"   {result['url']}")
    elif result.get("id"):
        print(f"   id: {result['id']}")


if __name__ == "__main__":
    main()

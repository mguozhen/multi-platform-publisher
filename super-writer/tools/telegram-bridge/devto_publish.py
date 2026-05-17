"""
Dev.to 发布 — 官方 REST API 直连。

  publish(title, body_md, tags=None, published=False) -> {ok, url, id} | {ok:False, error}

凭证: ~/.secrets/publishing-platforms.env → DEVTO_API_KEY

首发建议 published=False（存草稿），人审后再上线。

CLI: python3 devto_publish.py <markdown_file> "标题" tag1,tag2
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

API = "https://dev.to/api/articles"
SECRETS = Path.home() / ".secrets" / "publishing-platforms.env"


def _key() -> str:
    if SECRETS.exists():
        for ln in SECRETS.read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if ln.startswith("DEVTO_API_KEY=") and not ln.startswith("#"):
                return ln.split("=", 1)[1].strip()
    return os.environ.get("DEVTO_API_KEY", "")


def publish(title: str, body_md: str, tags: list | None = None,
            published: bool = False) -> dict:
    """发一篇 Dev.to 文章。published=False → 草稿。"""
    key = _key()
    if not key:
        return {"ok": False, "error": "缺 DEVTO_API_KEY (~/.secrets/publishing-platforms.env)"}
    article: dict = {
        "title": title[:128],
        "body_markdown": body_md,
        "published": bool(published),
    }
    if tags:
        # dev.to tag: 全小写、无空格、≤4 个
        article["tags"] = [t.lower().replace(" ", "").replace("-", "")[:30]
                           for t in tags[:4]]
    data = json.dumps({"article": article}).encode("utf-8")
    req = urllib.request.Request(
        API, data=data, method="POST",
        headers={"api-key": key, "Content-Type": "application/json",
                 "User-Agent": "selfmedia-bridge"})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            d = json.loads(r.read().decode("utf-8"))
        return {"ok": True, "url": d.get("url"), "id": d.get("id"),
                "published": d.get("published")}
    except urllib.error.HTTPError as e:
        return {"ok": False,
                "error": f"HTTP {e.code}: {e.read().decode('utf-8','replace')[:300]}"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def main() -> None:
    args = sys.argv[1:]
    if len(args) < 2:
        print('用法: python3 devto_publish.py <markdown_file> "标题" [tag1,tag2]')
        sys.exit(1)
    body = Path(args[0]).expanduser().read_text(encoding="utf-8")
    tags = args[2].split(",") if len(args) > 2 else None
    r = publish(args[1], body, tags=tags, published=False)
    print(json.dumps(r, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

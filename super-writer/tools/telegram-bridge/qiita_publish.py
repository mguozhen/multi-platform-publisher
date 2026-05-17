"""
Qiita 发布 — 官方 REST API 直连。

  publish(title, body_md, tags=None, private=True) -> {ok, url, id} | {ok:False, error}

凭证: ~/.secrets/publishing-platforms.env → QIITA_API_TOKEN

首发建议 private=True（限定公开），日文人审后再公开。

CLI: python3 qiita_publish.py <markdown_file> "タイトル" tag1,tag2
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

API = "https://qiita.com/api/v2/items"
SECRETS = Path.home() / ".secrets" / "publishing-platforms.env"


def _token() -> str:
    if SECRETS.exists():
        for ln in SECRETS.read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if ln.startswith("QIITA_API_TOKEN=") and not ln.startswith("#"):
                return ln.split("=", 1)[1].strip()
    return os.environ.get("QIITA_API_TOKEN", "")


def publish(title: str, body_md: str, tags: list | None = None,
            private: bool = True) -> dict:
    """发一篇 Qiita 文章。private=True → 限定公开。Qiita 文章必须带 ≥1 个 tag。"""
    token = _token()
    if not token:
        return {"ok": False, "error": "缺 QIITA_API_TOKEN (~/.secrets/publishing-platforms.env)"}
    tag_objs = [{"name": t, "versions": []} for t in (tags or ["AI"])[:5]]
    payload = {
        "title": title[:255],
        "body": body_md,
        "tags": tag_objs,
        "private": bool(private),
        "tweet": False,
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        API, data=data, method="POST",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json",
                 "User-Agent": "selfmedia-bridge"})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            d = json.loads(r.read().decode("utf-8"))
        return {"ok": True, "url": d.get("url"), "id": d.get("id"),
                "private": d.get("private")}
    except urllib.error.HTTPError as e:
        return {"ok": False,
                "error": f"HTTP {e.code}: {e.read().decode('utf-8','replace')[:300]}"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def main() -> None:
    args = sys.argv[1:]
    if len(args) < 2:
        print('用法: python3 qiita_publish.py <markdown_file> "タイトル" [tag1,tag2]')
        sys.exit(1)
    body = Path(args[0]).expanduser().read_text(encoding="utf-8")
    tags = args[2].split(",") if len(args) > 2 else None
    r = publish(args[1], body, tags=tags, private=True)
    print(json.dumps(r, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

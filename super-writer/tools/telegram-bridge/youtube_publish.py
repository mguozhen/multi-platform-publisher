"""
YouTube 发布 — Data API v3，OAuth refresh token，resumable 上传。

  publish(video_path, title, description="", tags=None, privacy="public") -> {ok, url, id}

凭证: ~/.secrets/publishing-platforms.env
  YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET / YOUTUBE_REFRESH_TOKEN

CLI: python3 youtube_publish.py <video> "title" "desc" tag1,tag2 [privacy]
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=FutureWarning)

SECRETS = Path.home() / ".secrets" / "publishing-platforms.env"
TOKEN_URI = "https://oauth2.googleapis.com/token"


def _env() -> dict:
    d = {}
    if SECRETS.exists():
        for ln in SECRETS.read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k, v = ln.split("=", 1)
                d[k.strip()] = v.strip()
    return d


def publish(video_path: str, title: str, description: str = "",
            tags: list | None = None, privacy: str = "public") -> dict:
    """上传一个视频到 YouTube。privacy: public / unlisted / private。"""
    env = _env()
    cid = env.get("YOUTUBE_CLIENT_ID")
    csec = env.get("YOUTUBE_CLIENT_SECRET")
    rtok = env.get("YOUTUBE_REFRESH_TOKEN")
    if not (cid and csec and rtok):
        return {"ok": False, "error": "缺 YOUTUBE_CLIENT_ID/SECRET/REFRESH_TOKEN"}
    p = Path(video_path).expanduser()
    if not p.exists():
        return {"ok": False, "error": f"视频不存在: {p}"}
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError as e:
        return {"ok": False, "error": f"缺 google 库: {e}"}

    creds = Credentials(None, refresh_token=rtok, client_id=cid,
                        client_secret=csec, token_uri=TOKEN_URI)
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": (tags or [])[:15],
            "categoryId": "28",          # Science & Technology
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }
    try:
        youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
        media = MediaFileUpload(str(p), chunksize=-1, resumable=True)
        req = youtube.videos().insert(part="snippet,status", body=body,
                                      media_body=media)
        resp = None
        while resp is None:
            _, resp = req.next_chunk()
        vid = resp["id"]
        return {"ok": True, "id": vid,
                "url": f"https://www.youtube.com/watch?v={vid}"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:400]}"}


def main() -> None:
    args = sys.argv[1:]
    if len(args) < 2:
        print('用法: python3 youtube_publish.py <video> "title" "desc" [tag1,tag2] [privacy]')
        sys.exit(1)
    desc = args[2] if len(args) > 2 else ""
    tags = args[3].split(",") if len(args) > 3 else None
    privacy = args[4] if len(args) > 4 else "public"
    import json
    r = publish(args[0], args[1], desc, tags, privacy)
    print(json.dumps(r, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

"""
X (Twitter) 发推 — OAuth 1.0a User Context，发单条 / 发 thread。

  post_tweet(text, reply_to=None)  -> tweet_id
  post_thread(tweets)              -> {first_id, url, ids}
  split_numbered_thread(text)      -> list[str]   按 "N/M" 行拆 thread

凭证 (~/.secrets/x.env):
  X_API_KEY              Consumer Key  (X 开发者后台 → App → Keys → API Key)
  X_API_SECRET           Consumer Secret
  X_ACCESS_TOKEN         Access Token        (需 App 权限为 Read and Write)
  X_ACCESS_TOKEN_SECRET  Access Token Secret
  X_HANDLE               账号 handle (拼 URL 用)

⚠️ App 权限若是 read-only，发推 403 — 去后台改 Read and Write 后**重新生成** access token。

CLI
  python3 x_post.py --thread "全文..."     拆分并发 thread
  python3 x_post.py --tweet "一条推文"
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

X_ENV = Path.home() / ".secrets" / "x.env"
API = "https://api.twitter.com/2/tweets"
UPLOAD = "https://upload.twitter.com/1.1/media/upload.json"


# ───────────────────── creds ─────────────────────────
def _creds() -> dict:
    c = {}
    if X_ENV.exists():
        for ln in X_ENV.read_text().splitlines():
            ln = ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k, v = ln.split("=", 1)
                c[k.strip()] = v.strip().strip('"').strip("'")
    miss = [k for k in ("X_API_KEY", "X_API_SECRET",
                        "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET")
            if not c.get(k)]
    if miss:
        raise RuntimeError(f"x.env 缺凭证: {', '.join(miss)} — 见 x_post.py 头部说明")
    return c


# ─────────────────── OAuth 1.0a ──────────────────────
def _q(s: str) -> str:
    return urllib.parse.quote(str(s), safe="~")


def _auth_header(method: str, url: str, c: dict,
                 extra: dict | None = None) -> str:
    """OAuth 1.0a 签名。

    JSON body 不进基串。但 query-string 参数 (extra) 必须进基串 —
    media/upload v1.1 的 INIT/APPEND/FINALIZE/STATUS 参数走 query string。
    """
    oauth = {
        "oauth_consumer_key": c["X_API_KEY"],
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": c["X_ACCESS_TOKEN"],
        "oauth_version": "1.0",
    }
    sign_params = dict(oauth)
    if extra:
        sign_params.update({k: str(v) for k, v in extra.items()})
    param_str = "&".join(f"{_q(k)}={_q(sign_params[k])}"
                         for k in sorted(sign_params))
    base = "&".join([method.upper(), _q(url), _q(param_str)])
    key = f"{_q(c['X_API_SECRET'])}&{_q(c['X_ACCESS_TOKEN_SECRET'])}"
    sig = base64.b64encode(
        hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()).decode()
    oauth["oauth_signature"] = sig
    return "OAuth " + ", ".join(
        f'{_q(k)}="{_q(v)}"' for k, v in sorted(oauth.items()))


# ─────────────────── video upload (v1.1) ──────────────────
def _upload_call(method: str, params: dict, c: dict,
                 body: bytes = b"", content_type: str | None = None) -> dict:
    """打 upload.twitter.com，params 进 query string 并签名。"""
    qs = urllib.parse.urlencode(params)
    full = f"{UPLOAD}?{qs}"
    headers = {"Authorization": _auth_header(method, UPLOAD, c, params)}
    if content_type:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(full, data=body if body else None,
                                 method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            raw = r.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:400]
        raise RuntimeError(f"X media/upload HTTP {e.code}: {detail}") from e


def upload_video(path: str) -> str:
    """分块上传一个 mp4 到 X，返回 media_id（可挂到推文）。"""
    c = _creds()
    p = Path(path).expanduser()
    if not p.exists():
        raise RuntimeError(f"视频不存在: {p}")
    total = p.stat().st_size
    # INIT
    init = _upload_call("POST", {
        "command": "INIT", "total_bytes": total,
        "media_type": "video/mp4", "media_category": "tweet_video"}, c)
    media_id = init.get("media_id_string")
    if not media_id:
        raise RuntimeError(f"INIT 未返回 media_id: {init}")
    # APPEND — 4MB 分块，binary 走 multipart，参数走 query string
    chunk = 4 * 1024 * 1024
    with p.open("rb") as f:
        idx = 0
        while True:
            data = f.read(chunk)
            if not data:
                break
            boundary = "----xvid" + secrets.token_hex(8)
            mp = bytearray()
            mp.extend(f"--{boundary}\r\n".encode())
            mp.extend(b'Content-Disposition: form-data; name="media"\r\n')
            mp.extend(b"Content-Type: application/octet-stream\r\n\r\n")
            mp.extend(data)
            mp.extend(f"\r\n--{boundary}--\r\n".encode())
            _upload_call("POST", {
                "command": "APPEND", "media_id": media_id,
                "segment_index": idx}, c, bytes(mp),
                f"multipart/form-data; boundary={boundary}")
            idx += 1
    # FINALIZE
    fin = _upload_call("POST", {"command": "FINALIZE",
                                "media_id": media_id}, c)
    # 视频要异步转码，轮询 STATUS
    info = fin.get("processing_info")
    waited = 0
    while info and info.get("state") in ("pending", "in_progress"):
        wait = min(info.get("check_after_secs", 5), 15)
        time.sleep(wait)
        waited += wait
        if waited > 300:
            raise RuntimeError("X 视频转码超时 (>5min)")
        st = _upload_call("GET", {"command": "STATUS",
                                  "media_id": media_id}, c)
        info = st.get("processing_info")
    if info and info.get("state") == "failed":
        raise RuntimeError(f"X 视频转码失败: {info.get('error')}")
    return media_id


# ─────────────────── public API ──────────────────────
def post_tweet(text: str, reply_to: str | None = None,
               media_ids: list | None = None) -> str:
    """发一条推文，返回 tweet_id。reply_to 接龙；media_ids 挂视频/图片。"""
    c = _creds()
    payload: dict = {}
    if text:
        payload["text"] = text
    if reply_to:
        payload["reply"] = {"in_reply_to_tweet_id": reply_to}
    if media_ids:
        payload["media"] = {"media_ids": [str(m) for m in media_ids]}
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        API, data=body, method="POST",
        headers={"Authorization": _auth_header("POST", API, c),
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:400]
        raise RuntimeError(f"X API HTTP {e.code}: {detail}") from e
    tid = (resp.get("data") or {}).get("id")
    if not tid:
        raise RuntimeError(f"发推未返回 id: {resp}")
    return tid


def post_thread(tweets: list[str], delay: float = 2.0) -> dict:
    """按顺序发 thread，每条接在上一条下面。返回 {first_id, url, ids}。"""
    over = [(i + 1, len(t)) for i, t in enumerate(tweets) if len(t) > 280]
    if over:
        raise RuntimeError(f"以下推文超 280 字: {over}")
    ids: list[str] = []
    prev = None
    for t in tweets:
        tid = post_tweet(t, reply_to=prev)
        ids.append(tid)
        prev = tid
        time.sleep(delay)
    handle = _creds().get("X_HANDLE", "i").lstrip("@")
    return {"first_id": ids[0], "ids": ids,
            "url": f"https://x.com/{handle}/status/{ids[0]}"}


def post_video(text: str, video_path: str) -> dict:
    """上传视频并发一条带视频的推文。返回 {id, url}。"""
    if len(text) > 280:
        raise RuntimeError(f"推文 {len(text)} 字，超 280")
    media_id = upload_video(video_path)
    tid = post_tweet(text, media_ids=[media_id])
    handle = _creds().get("X_HANDLE", "i").lstrip("@")
    return {"id": tid, "url": f"https://x.com/{handle}/status/{tid}"}


def split_numbered_thread(text: str) -> list[str]:
    """按 'N/M' 行把整段 thread 拆成多条推文。"""
    parts: list[str] = []
    cur: list[str] = []
    for ln in text.splitlines():
        if re.match(r"^\s*\d+\s*/\s*\d+\s*$", ln) and cur:
            parts.append("\n".join(cur).strip())
            cur = [ln]
        else:
            cur.append(ln)
    if cur:
        parts.append("\n".join(cur).strip())
    return [p for p in parts if p]


# ─────────────────────── cli ─────────────────────────
def main() -> None:
    args = sys.argv[1:]
    if len(args) == 2 and args[0] == "--tweet":
        print(f"✅ posted: {post_tweet(args[1])}")
    elif len(args) == 2 and args[0] == "--thread":
        tweets = split_numbered_thread(args[1])
        print(f"拆出 {len(tweets)} 条，发送中…")
        r = post_thread(tweets)
        print(f"✅ thread 已发: {r['url']}")
    elif len(args) == 3 and args[0] == "--video":
        # --video <mp4path> "<文案>"
        print(f"上传视频 {args[1]} …")
        r = post_video(args[2], args[1])
        print(f"✅ 视频推文已发: {r['url']}")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()

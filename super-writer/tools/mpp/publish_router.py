"""把改写好的内容路由到具体的平台发布器（复用 super-writer 现有产物）。

成功返回 {ok: True, url: ..., note: ...}；失败返回 {ok: False, error: ...}。
所有发布器都是 self-media/tools/telegram-bridge/ + tools/linkedin/ 已有的。

⚠️ 设计原则（不可撤回的留人审）:
  - wechat 永远进草稿箱,不直发
  - 其他平台按用户「真发」策略直发
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
import json
from pathlib import Path

HOME = Path.home()
BRIDGE = HOME / "self-media" / "tools" / "telegram-bridge"
LINKEDIN = HOME / "self-media" / "tools" / "linkedin"

# make publishers importable
for p in (BRIDGE, LINKEDIN):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


def publish(platform: str, text: str, *, title: str | None = None,
            tags: list[str] | None = None, link: str | None = None) -> dict:
    """单平台发布。link 是 GitHub/项目链接,会按平台规矩处理。"""
    platform = platform.lower()
    try:
        if platform == "x":
            return _publish_x(text)
        if platform == "linkedin":
            return _publish_linkedin(text, link=link)
        if platform == "devto":
            return _publish_devto(text, title=title, tags=tags or [])
        if platform == "qiita":
            return _publish_qiita(text, title=title, tags=tags or [])
        if platform == "wechat":
            return _publish_wechat(text, title=title)
        return {"ok": False, "error": f"unsupported platform: {platform}"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"[:400]}


# ───────────────────────── X ─────────────────────────
def _publish_x(text: str) -> dict:
    import x_post as xp  # type: ignore
    tid = xp.post_tweet(text)
    handle = _x_handle()
    return {"ok": True, "url": f"https://x.com/{handle}/status/{tid}",
            "note": "X 单条长文（playbook: 绝不发 thread）"}


def _x_handle() -> str:
    env = HOME / ".secrets" / "x.env"
    if env.exists():
        for ln in env.read_text(encoding="utf-8").splitlines():
            if ln.startswith("X_HANDLE="):
                return ln.split("=", 1)[1].strip()
    return "GuoHunter95258"


# ───────────────────────── LinkedIn ─────────────────────────
def _publish_linkedin(text: str, *, link: str | None = None) -> dict:
    """LinkedIn 正文不挂链；link 走第一条评论（playbook 推广开源项目铁律）。"""
    env = _read_env(HOME / ".secrets" / "linkedin.env")
    tok = env.get("LINKEDIN_ACCESS_TOKEN", "")
    urn = env.get("LINKEDIN_PERSON_URN", "")
    if not tok or not urn:
        return {"ok": False, "error": "missing LINKEDIN_ACCESS_TOKEN / PERSON_URN"}

    # 1) post
    body = {
        "author": urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE",
            }},
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }
    req = urllib.request.Request(
        "https://api.linkedin.com/v2/ugcPosts",
        data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": f"Bearer {tok}",
                 "X-Restli-Protocol-Version": "2.0.0",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        share_urn = r.headers.get("x-restli-id") or r.headers.get("X-RestLi-Id")
    if not share_urn:
        return {"ok": False, "error": "linkedin post returned no urn"}

    url = f"https://www.linkedin.com/feed/update/{share_urn}"
    note = "LinkedIn 主贴（playbook: 不挂链）"

    # 2) optional first-comment link
    if link:
        cmt = (f"Open source — {link}\n\nWrite once; it rewrites into "
               "platform-native versions for 13 platforms. A GitHub star helps.")
        creq = urllib.request.Request(
            "https://api.linkedin.com/v2/socialActions/"
            + urllib.parse.quote(share_urn, safe="") + "/comments",
            data=json.dumps({"actor": urn, "message": {"text": cmt}}).encode(),
            method="POST",
            headers={"Authorization": f"Bearer {tok}",
                     "X-Restli-Protocol-Version": "2.0.0",
                     "Content-Type": "application/json"})
        try:
            urllib.request.urlopen(creq, timeout=20)
            note += " · 链接已发为第一条评论"
        except Exception as e:
            note += f" · 评论链接失败: {e}"
    return {"ok": True, "url": url, "note": note}


# ───────────────────────── Dev.to ─────────────────────────
def _publish_devto(text: str, *, title: str | None, tags: list[str]) -> dict:
    if not title:
        # 第一行作为标题
        first, _, rest = text.partition("\n")
        title = first.strip().lstrip("#").strip()
        text = rest.strip()
    import devto_publish as dp  # type: ignore
    r = dp.publish(title=title, body_md=text, tags=tags[:4], published=True)
    if not r.get("ok"):
        return {"ok": False, "error": r.get("error", "devto publish failed")}
    return {"ok": True, "url": r["url"], "note": f"Dev.to (真发, tags={tags[:4]})"}


# ───────────────────────── Qiita ─────────────────────────
def _publish_qiita(text: str, *, title: str | None, tags: list[str]) -> dict:
    if not title:
        m = re.search(r"^#\s+(.+)$", text, re.M)
        title = m.group(1).strip() if m else "公開"
    import qiita_publish as qp  # type: ignore
    # 用户「真发」策略 → private=False
    r = qp.publish(title=title, body_md=text, tags=tags[:4] or ["OSS"], private=False)
    if not r.get("ok"):
        return {"ok": False, "error": r.get("error", "qiita publish failed")}
    return {"ok": True, "url": r["url"], "note": f"Qiita 公開 (tags={tags[:4]})"}


# ───────────────────────── WeChat ─────────────────────────
def _publish_wechat(text: str, *, title: str | None) -> dict:
    """WeChat 安全设计：永远只进草稿箱，群发由 Hunter 手动确认。"""
    if not title:
        m = re.search(r"^#\s+(.+)$", text, re.M)
        title = m.group(1).strip() if m else "新文章"
        text = re.sub(r"^#\s+.+\n", "", text, count=1)
    import wechat_draft as wd  # type: ignore
    r = wd.add_draft(title=title, body_md=text.strip())
    if not r.get("ok"):
        return {"ok": False, "error": r.get("error", "wechat draft failed")}
    return {"ok": True,
            "url": "https://mp.weixin.qq.com/cgi-bin/appmsg?action=list_draft",
            "note": f"WeChat 已进草稿箱 (media_id={r['media_id']}, 群发由你手动确认)"}


# ───────────────────────── helpers ─────────────────────────
def _read_env(path: Path) -> dict:
    out = {}
    if path.exists():
        for ln in path.read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if "=" in ln and not ln.startswith("#"):
                k, _, v = ln.partition("=")
                out[k.strip()] = v.strip().strip('"').strip("'")
    return out

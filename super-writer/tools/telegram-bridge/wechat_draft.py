"""
公众号草稿箱 — 微信公众平台官方 API.

  add_draft(title, body_md)   markdown 正文 → HTML → 推到草稿箱
  upload_thumb(image_path)    一次性: 上传永久封面图，拿 thumb media_id

凭证 (~/.secrets/wechat.env 或进程环境变量):
  WECHAT_APPID            公众号 AppID
  WECHAT_SECRET           公众号 AppSecret
  WECHAT_THUMB_MEDIA_ID   draft/add 必填的封面图 media_id
                          (跑 `python3 wechat_draft.py --upload-thumb 封面.jpg` 拿到)

前置条件 (代码解决不了，需在公众号后台配):
  - 出口 IP 必须加入公众号后台「设置与开发 → 基本配置 → IP 白名单」
    (errcode 40164 = IP 不在白名单)
  - 需「已认证的服务号」才有 draft API 权限 (errcode 48001 = 无此接口权限)

CLI
  python3 wechat_draft.py --upload-thumb 封面.jpg   上传封面，打印 media_id
  python3 wechat_draft.py --test                    推一条测试草稿
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

HOME = Path.home()
SECRETS = HOME / ".secrets"
ENV_FILE = SECRETS / "wechat.env"
TOKEN_CACHE = SECRETS / ".wechat_token.json"
API = "https://api.weixin.qq.com"


# ───────────────────────── creds ─────────────────────────
def _load_creds() -> dict:
    creds = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                creds[k.strip()] = v.strip().strip('"').strip("'")
    for k in ("WECHAT_APPID", "WECHAT_SECRET", "WECHAT_APPSECRET",
              "WECHAT_THUMB_MEDIA_ID"):
        if os.environ.get(k):
            creds[k] = os.environ[k]
    # 兼容 WECHAT_APPSECRET 别名
    if not creds.get("WECHAT_SECRET") and creds.get("WECHAT_APPSECRET"):
        creds["WECHAT_SECRET"] = creds["WECHAT_APPSECRET"]
    return creds


def _http_get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def _http_post(url: str, payload: dict) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


# ───────────────────── access token ─────────────────────
def _access_token(creds: dict) -> str:
    """Fetch (and cache) the API access_token. Valid 7200s."""
    if TOKEN_CACHE.exists():
        try:
            cached = json.loads(TOKEN_CACHE.read_text())
            if cached.get("appid") == creds.get("WECHAT_APPID") \
                    and cached.get("expires_at", 0) > time.time() + 120:
                return cached["token"]
        except Exception:  # noqa: BLE001
            pass
    appid = creds.get("WECHAT_APPID", "")
    secret = creds.get("WECHAT_SECRET", "")
    if not appid or not secret:
        raise RuntimeError("缺少 WECHAT_APPID / WECHAT_SECRET (写入 ~/.secrets/wechat.env)")
    url = (f"{API}/cgi-bin/token?grant_type=client_credential"
           f"&appid={urllib.parse.quote(appid)}&secret={urllib.parse.quote(secret)}")
    resp = _http_get(url)
    if "access_token" not in resp:
        raise RuntimeError(f"拿 access_token 失败: {resp}")
    SECRETS.mkdir(exist_ok=True)
    TOKEN_CACHE.write_text(json.dumps({
        "appid": appid,
        "token": resp["access_token"],
        "expires_at": time.time() + int(resp.get("expires_in", 7200)),
    }))
    return resp["access_token"]


# ─────────────────── 公众号深度文渲染器 ───────────────────
# 严格复刻样本公众号排版：每行=一段，<p> 只留 14px 下边距（不要上边距，
# 否则空白翻倍）；小标题用衬线字体 + 上方细分隔线；图片居中圆角带说明。
_FONT = ("'Noto Sans SC','PingFang SC','Microsoft YaHei',"
         "-apple-system,sans-serif")
_SERIF = "'Noto Serif SC','Songti SC',STSong,Georgia,serif"
_MONO = "'JetBrains Mono','SF Mono',Menlo,Consolas,monospace"

_P = (f'style="font-family:{_FONT};font-size:15px;color:rgb(74,74,69);'
      'line-height:1.9;margin:0 0 14px;word-break:break-all;"')
_H2 = (f'style="font-family:{_SERIF};font-size:22px;font-weight:700;'
       'line-height:1.4;color:#1a1a18;margin:18px 0 16px;'
       'word-break:break-all;"')
_H3 = (f'style="font-family:{_SERIF};font-size:18px;font-weight:700;'
       'line-height:1.4;color:#1a1a18;margin:16px 0 12px;"')
_EYE = (f'style="font-family:{_MONO};font-size:12px;color:rgb(207,68,54);'
        'letter-spacing:2px;text-transform:uppercase;margin:0 0 8px;"')
_CAP = (f'style="font-family:{_FONT};font-size:12px;color:rgb(138,138,130);'
        'text-align:center;margin:0 0 16px;"')
_DIV = ('<section style="border-top:1px solid rgba(120,120,112,0.18);'
        'height:0;margin:22px 0;"></section>')


def _md_to_html(md: str) -> str:
    """渲染成公众号深度文 HTML（每行=一段）。"""
    out: list[str] = []
    for raw in md.splitlines():
        line = raw.strip()
        if not line:
            continue
        # 图片 ![说明](url) — 居中、圆角、带说明文字
        m = re.match(r"^!\[(.*?)\]\((.+?)\)$", line)
        if m:
            cap, url = m.group(1), m.group(2)
            out.append('<section style="text-align:center;margin:6px 0;">'
                       f'<img src="{html.escape(url, quote=True)}" '
                       'style="max-width:100%;border-radius:6px;'
                       'width:100%;height:auto;"/></section>')
            if cap:
                out.append(f"<p {_CAP}>{html.escape(cap)}</p>")
            continue
        # 小标题（衬线 + 上方分隔线）
        m = re.match(r"^(#{1,3})\s+(.*)$", line)
        if m:
            txt = _inline(m.group(2))
            if len(m.group(1)) <= 2:
                out.append(_DIV)
                out.append(f"<h2 {_H2}>{txt}</h2>")
            else:
                out.append(f"<h3 {_H3}>{txt}</h3>")
            continue
        # 顶部 eyebrow 标签（OPEN SOURCE 这类）
        if not out and re.match(r"^[A-Z][A-Z ]{2,28}$", line):
            out.append(f"<p {_EYE}>{html.escape(line)}</p>")
            continue
        # 导语 / callout 块（> 开头）
        if line.startswith(">"):
            txt = _inline(line.lstrip("> ").strip())
            out.append('<section style="background:#f6f6f7;'
                       'border-left:3px solid rgb(207,68,54);'
                       'border-radius:4px;padding:14px 18px;margin:0 0 20px;">'
                       f'<p style="font-family:{_FONT};font-size:14px;'
                       'color:rgb(90,90,86);line-height:1.85;margin:0;">'
                       f'{txt}</p></section>')
            continue
        # 列表项打平成段（绝不出 <ul>/<li>）
        line = re.sub(r"^[-*]\s+", "", line)
        out.append(f"<p {_P}>{_inline(line)}</p>")
    body = "\n".join(out)
    return f'<section style="max-width:640px;margin:0 auto;">{body}</section>'


def _inline(text: str) -> str:
    text = html.escape(text, quote=False)
    # **重点** → 划线式强调（样本同款 strong）
    text = re.sub(r"\*\*(.+?)\*\*",
                  r'<strong style="color:rgb(26,26,24);font-weight:600;">'
                  r"\1</strong>", text)
    text = re.sub(r"`([^`]+?)`",
                  r'<code style="background:#f4f4f5;border-radius:3px;'
                  r'padding:1px 5px;font-size:13px;color:#c0341d;">\1</code>',
                  text)
    return text


# ───────────────────── public API ───────────────────────
def upload_thumb(image_path: str) -> dict:
    """上传永久封面图素材，返回 {ok, media_id}。"""
    creds = _load_creds()
    tok = _access_token(creds)
    p = Path(image_path).expanduser()
    if not p.exists():
        return {"ok": False, "error": f"图片不存在: {p}"}
    boundary = "----wechatthumb" + str(int(time.time()))
    body = bytearray()
    body += f"--{boundary}\r\n".encode()
    body += (f'Content-Disposition: form-data; name="media"; '
             f'filename="{p.name}"\r\n').encode()
    body += b"Content-Type: application/octet-stream\r\n\r\n"
    body += p.read_bytes()
    body += f"\r\n--{boundary}--\r\n".encode()
    url = f"{API}/cgi-bin/material/add_material?access_token={tok}&type=image"
    req = urllib.request.Request(
        url, data=bytes(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        resp = json.loads(r.read().decode("utf-8"))
    if resp.get("media_id"):
        return {"ok": True, "media_id": resp["media_id"]}
    return {"ok": False, "error": f"上传封面失败: {resp}"}


def _upload_content_image(image_path: str, tok: str) -> str:
    """上传正文内图片，返回可用于 draft content 的微信 URL（失败返回空串）。"""
    p = Path(image_path).expanduser()
    if not p.exists():
        return ""
    boundary = "----wxcontentimg" + str(int(time.time() * 1000))
    body = bytearray()
    body += f"--{boundary}\r\n".encode()
    body += (f'Content-Disposition: form-data; name="media"; '
             f'filename="{p.name}"\r\n').encode()
    body += b"Content-Type: application/octet-stream\r\n\r\n"
    body += p.read_bytes()
    body += f"\r\n--{boundary}--\r\n".encode()
    url = f"{API}/cgi-bin/media/uploadimg?access_token={tok}"
    req = urllib.request.Request(
        url, data=bytes(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.loads(r.read().decode("utf-8"))
        return resp.get("url", "")
    except Exception:  # noqa: BLE001
        return ""


def _embed_inline_images(body_md: str, tok: str,
                         image_map: dict | None = None) -> str:
    """把正文里的 [图：说明] 标记换成**真实素材**配图（图文并茂）。

    image_map: {说明文字: 本地图片路径} — 用真实截图 / 实拍图，不 AI 发散生成。
    未在 image_map 里的标记直接删掉（宁缺毋滥）。
    """
    image_map = image_map or {}
    markers = re.findall(r"\[图[:：](.+?)\]", body_md)
    if not markers:
        return body_md
    for cap in markers:
        marker_re = re.compile(r"\[图[:：]" + re.escape(cap) + r"\]")
        path = image_map.get(cap, "")
        repl = ""
        if path and Path(path).expanduser().exists():
            url = _upload_content_image(str(Path(path).expanduser()), tok)
            if url:
                repl = f"![{cap}]({url})"
        body_md = marker_re.sub(repl, body_md, count=1)
    return body_md


def _embed_inline_images_local(body_md: str, image_map: dict | None) -> str:
    """预览用：把 [图：图注] 换成 file:// 本地图片（不上传微信）。"""
    image_map = image_map or {}
    for cap in re.findall(r"\[图[:：](.+?)\]", body_md):
        marker_re = re.compile(r"\[图[:：]" + re.escape(cap) + r"\]")
        path = image_map.get(cap, "")
        repl = ""
        if path and Path(path).expanduser().exists():
            repl = f"![{cap}](file://{Path(path).expanduser()})"
        body_md = marker_re.sub(repl, body_md, count=1)
    return body_md


def preview(title: str, body_md: str, image_map: dict | None = None,
            out_path: str | None = None) -> str:
    """把文章渲染成本地 HTML（公众号白底样式），返回路径。发布前看排版用。

    用 Chrome 截图: chrome --headless=new --screenshot=preview.png
                     --window-size=760,7600 file://<返回路径>
    """
    body = _embed_inline_images_local(body_md, image_map)
    inner = _md_to_html(body)
    page = (
        '<!doctype html><html><head><meta charset="utf-8">'
        '<style>html,body{margin:0;background:#ebebeb;}'
        '.wrap{max-width:709px;margin:0 auto;background:#fff;'
        'padding:22px 20px 60px;}'
        f'.t{{font-family:{_FONT};font-size:22px;font-weight:700;'
        'color:#1a1a18;line-height:1.4;margin:6px 0 8px;}}'
        f'.m{{font-family:{_FONT};font-size:13px;color:#9a9a96;'
        'margin-bottom:20px;border-bottom:1px solid #eee;'
        'padding-bottom:14px;}}'
        '</style></head><body><div class="wrap">'
        f'<div class="t">{html.escape(title)}</div>'
        '<div class="m">Hunter 在跑 · 草稿预览</div>'
        f'{inner}</div></body></html>'
    )
    out = Path(out_path).expanduser() if out_path else (
        HOME / "self-media" / "content" / "_covers" / "preview.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    return str(out)


def _auto_cover(title: str) -> str:
    """没配静态封面时，用 image_gen 生成一张并上传，返回 media_id（失败返回空串）。"""
    try:
        import image_gen
        covers = HOME / "self-media" / "content" / "_covers"
        out = covers / f"wechat-{int(time.time())}.png"
        image_gen.generate_image(
            image_gen.cover_prompt(title, "wechat"), out, size="1536x1024")
        r = upload_thumb(str(out))
        return r.get("media_id", "") if r.get("ok") else ""
    except Exception:  # noqa: BLE001
        return ""


def add_draft(title: str, body_md: str, digest: str = "",
              cover_image: str | None = None,
              image_map: dict | None = None) -> dict:
    """把一篇文章推到公众号草稿箱。返回 {ok, media_id} 或 {ok:False, error}。

    cover_image 给了就上传它当封面；否则用 WECHAT_THUMB_MEDIA_ID 或自动生成。
    image_map  {说明文字: 本地图片路径} — 正文 [图：…] 标记用的真实素材。
    """
    creds = _load_creds()
    thumb = creds.get("WECHAT_THUMB_MEDIA_ID", "")
    if not thumb and cover_image and Path(cover_image).expanduser().exists():
        up = upload_thumb(cover_image)
        thumb = up.get("media_id", "") if up.get("ok") else ""
    if not thumb:
        thumb = _auto_cover(title)
    if not thumb:
        return {"ok": False,
                "error": "草稿必须有封面图，且自动生成失败。两条路二选一: "
                         "(1) 配 image_gen 的 key (见 image_gen.py 头部说明)；"
                         "(2) 跑 `python3 wechat_draft.py --upload-thumb 封面.jpg` "
                         "把返回的 media_id 写进 ~/.secrets/wechat.env"}
    try:
        tok = _access_token(creds)
    except RuntimeError as e:
        return {"ok": False, "error": str(e)}

    # 图文并茂：把正文里的 [图：说明] 标记换成真实素材配图
    body_md = _embed_inline_images(body_md, tok, image_map)
    plain = re.sub(r"!\[.*?\]\(.*?\)", "", body_md)
    plain = re.sub(r"[#*`>_\-]", "", plain).strip()
    article = {
        "title": title[:64],
        "author": "Hunter",
        "digest": (digest or plain[:120]).strip(),
        "content": _md_to_html(body_md),
        "content_source_url": "",
        "thumb_media_id": thumb,
        "need_open_comment": 1,
        "only_fans_can_comment": 0,
    }
    resp = _http_post(f"{API}/cgi-bin/draft/add?access_token={tok}",
                      {"articles": [article]})
    if resp.get("media_id"):
        return {"ok": True, "media_id": resp["media_id"]}
    code = resp.get("errcode")
    hint = {
        40164: "出口 IP 不在公众号后台 IP 白名单",
        48001: "该公众号无 draft API 权限 (需已认证的服务号)",
        40001: "access_token 失效，删 ~/.secrets/.wechat_token.json 重试",
    }.get(code, "")
    return {"ok": False,
            "error": f"draft/add 失败 errcode={code} {resp.get('errmsg','')}"
                     + (f" — {hint}" if hint else "")}


# ──────────────────── 改草稿 (draft/update) ──────────────
def list_drafts(offset: int = 0, count: int = 20) -> dict:
    """列草稿箱。返回 {ok, total, items:[{media_id, index, title, update_time}]}。"""
    creds = _load_creds()
    try:
        tok = _access_token(creds)
    except RuntimeError as e:
        return {"ok": False, "error": str(e)}
    resp = _http_post(f"{API}/cgi-bin/draft/batchget?access_token={tok}",
                      {"offset": offset, "count": count, "no_content": 1})
    if resp.get("errcode"):
        return {"ok": False,
                "error": f"draft/batchget errcode={resp['errcode']} "
                         f"{resp.get('errmsg','')}"}
    items = []
    for it in resp.get("item", []):
        news = (it.get("content") or {}).get("news_item", [])
        for idx, art in enumerate(news):
            items.append({
                "media_id": it.get("media_id"),
                "index": idx,
                "title": art.get("title", ""),
                "update_time": it.get("update_time"),
            })
    return {"ok": True, "total": resp.get("total_count", 0), "items": items}


def get_draft(media_id: str) -> dict:
    """取一条草稿全文。返回 {ok, news_item:[...]}。"""
    creds = _load_creds()
    try:
        tok = _access_token(creds)
    except RuntimeError as e:
        return {"ok": False, "error": str(e)}
    resp = _http_post(f"{API}/cgi-bin/draft/get?access_token={tok}",
                      {"media_id": media_id})
    if resp.get("errcode"):
        return {"ok": False,
                "error": f"draft/get errcode={resp['errcode']} "
                         f"{resp.get('errmsg','')}"}
    return {"ok": True, "news_item": resp.get("news_item", [])}


def set_draft_cover(media_id: str, cover_image: str, index: int = 0) -> dict:
    """改一条草稿里第 index 篇文章的封面（保留原标题/正文/作者）。"""
    creds = _load_creds()
    try:
        tok = _access_token(creds)
    except RuntimeError as e:
        return {"ok": False, "error": str(e)}
    up = upload_thumb(cover_image)
    if not up.get("ok"):
        return {"ok": False, "error": f"封面上传失败: {up.get('error')}"}
    new_thumb = up["media_id"]
    got = get_draft(media_id)
    if not got.get("ok"):
        return got
    items = got["news_item"]
    if index >= len(items):
        return {"ok": False,
                "error": f"index {index} 越界（该草稿 {len(items)} 篇）"}
    art = items[index]
    article = {
        "title": art.get("title", ""),
        "author": art.get("author", ""),
        "digest": art.get("digest", ""),
        "content": art.get("content", ""),
        "content_source_url": art.get("content_source_url", ""),
        "thumb_media_id": new_thumb,
        "need_open_comment": art.get("need_open_comment", 0),
        "only_fans_can_comment": art.get("only_fans_can_comment", 0),
    }
    resp = _http_post(f"{API}/cgi-bin/draft/update?access_token={tok}",
                      {"media_id": media_id, "index": index,
                       "articles": article})
    if resp.get("errcode", 0) == 0:
        return {"ok": True, "media_id": media_id, "index": index,
                "thumb_media_id": new_thumb, "title": art.get("title", "")}
    return {"ok": False,
            "error": f"draft/update errcode={resp.get('errcode')} "
                     f"{resp.get('errmsg','')}"}


def delete_draft(media_id: str) -> dict:
    """删一条草稿。返回 {ok} 或 {ok:False, error}。"""
    creds = _load_creds()
    try:
        tok = _access_token(creds)
    except RuntimeError as e:
        return {"ok": False, "error": str(e)}
    resp = _http_post(f"{API}/cgi-bin/draft/delete?access_token={tok}",
                      {"media_id": media_id})
    if resp.get("errcode", 0) == 0:
        return {"ok": True, "media_id": media_id}
    return {"ok": False,
            "error": f"draft/delete errcode={resp.get('errcode')} "
                     f"{resp.get('errmsg','')}"}


# ─────────────────────── cli ────────────────────────────
def main() -> None:
    args = sys.argv[1:]
    if args and args[0] == "--delete-draft" and len(args) == 2:
        print(json.dumps(delete_draft(args[1]), ensure_ascii=False, indent=2))
    elif args and args[0] == "--list-drafts":
        r = list_drafts()
        print(json.dumps(r, ensure_ascii=False, indent=2))
    elif args and args[0] == "--set-cover" and len(args) >= 3:
        idx = int(args[3]) if len(args) > 3 else 0
        r = set_draft_cover(args[1], args[2], idx)
        print(json.dumps(r, ensure_ascii=False, indent=2))
    elif args and args[0] == "--upload-thumb" and len(args) == 2:
        r = upload_thumb(args[1])
        if r["ok"]:
            print(f"✅ thumb media_id: {r['media_id']}")
            print("把它写进 ~/.secrets/wechat.env:")
            print(f"  WECHAT_THUMB_MEDIA_ID={r['media_id']}")
        else:
            sys.exit(f"❌ {r['error']}")
    elif args and args[0] == "--test":
        r = add_draft("测试草稿 — 全平台抽卡引擎",
                      "# 这是一条测试\n\n如果你在草稿箱看到这条，**公众号 API 已打通**。")
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(__doc__)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把多篇独立草稿合并成一条「多图文」草稿。

为什么：个人主体订阅号每天只能群发 1 次。一天推 5 篇独立文章 =
最多 1 篇进粉丝的订阅号消息，其余只是「发布」，零推送。
多图文可以在一次群发里带 1 个头条 + 最多 7 个次条，全部触达。

用法：
  bundle_drafts.py <头条目录> <次条目录> [次条目录...] [--dry]
每个目录需含 article.md / wechat.html / cover.jpg / push_to_wechat.py（读其中的 TITLE/DIGEST）
"""
import io, json, os, pathlib, re, sys
import requests

API = "https://api.weixin.qq.com/cgi-bin"


def token():
    r = requests.get(f"{API}/token", params={
        "grant_type": "client_credential",
        "appid": os.environ["WECHAT_APPID"],
        "secret": os.environ["WECHAT_SECRET"]}, timeout=20).json()
    if "access_token" not in r:
        sys.exit(f"拿不到 token: {r}")
    return r["access_token"]


def meta_of(d: pathlib.Path):
    src = (d / "push_to_wechat.py").read_text(encoding="utf-8")
    title = re.search(r'TITLE\s*=\s*"([^"]*)"', src).group(1)
    digest = re.search(r'DIGEST\s*=\s*"([^"]*)"', src)
    return title, (digest.group(1) if digest else "")


def upload_cover(tok, path: pathlib.Path):
    with open(path, "rb") as f:
        r = requests.post(f"{API}/material/add_material",
                          params={"access_token": tok, "type": "image"},
                          files={"media": (path.name, f, "image/jpeg")}, timeout=60).json()
    if "media_id" not in r:
        sys.exit(f"封面上传失败 {path}: {r}")
    return r["media_id"]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry" in sys.argv
    if len(args) < 2:
        sys.exit("至少给 1 个头条 + 1 个次条目录")
    if len(args) > 8:
        sys.exit("多图文最多 8 篇（1 头条 + 7 次条）")

    tok = None if dry else token()
    articles = []
    for i, a in enumerate(args):
        d = pathlib.Path(a).expanduser()
        title, digest = meta_of(d)
        html = (d / "wechat.html").read_text(encoding="utf-8")
        print(f"  {'头条' if i == 0 else f'次条{i}'} · {title[:40]}  ({len(html)//1024} KB)")
        if dry:
            continue
        articles.append({
            "title": title, "author": "Agent101", "digest": digest,
            "content": html, "content_source_url": "",
            "thumb_media_id": upload_cover(tok, d / "cover.jpg"),
            "need_open_comment": 1, "only_fans_can_comment": 0,
        })
    if dry:
        print("\n(dry run，未提交)")
        return
    r = requests.post(f"{API}/draft/add", params={"access_token": tok},
                      data=json.dumps({"articles": articles}, ensure_ascii=False).encode("utf-8"),
                      timeout=120).json()
    if "media_id" not in r:
        sys.exit(f"创建失败: {r}")
    print(f"\n✓ 多图文草稿已创建（{len(articles)} 篇）: {r['media_id']}")
    print("  后台草稿箱里是一条，群发一次全部触达粉丝。")


if __name__ == "__main__":
    main()

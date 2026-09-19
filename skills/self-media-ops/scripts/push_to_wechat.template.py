#!/usr/bin/env python3
"""把排好版的文章直接推进公众号后台草稿箱。

用法：
    export WECHAT_APPID=你的appid
    export WECHAT_SECRET=你的secret
    python3 push_to_wechat.py

做的事：
    1. 用 appid/secret 换 access_token
    2. 把封面图上传成永久素材，拿 thumb_media_id
    3. 把正文里内嵌的 base64 配图逐张上传，换成微信自己的图片地址
       （微信不认 base64，这一步不做的话正文里的图全是空的）
    4. 调草稿箱接口建一篇草稿

跑完去公众号后台「草稿箱」就能看到，排版和图片都在，直接改标题发布即可。
"""
import os, re, io, json, base64, sys, pathlib
import requests

API = "https://api.weixin.qq.com/cgi-bin"
HERE = pathlib.Path(__file__).resolve().parent
PKG = HERE

TITLE  = "AIUC 融资 4000 万美元：给 AI Agent 卖保险"      # ≤ 64 字符
AUTHOR = "Agent101"                                    # ≤ 8 个汉字
DIGEST = "Anthropic 第一个产品雇员创办的公司：给 agent 定标准、做对抗测试、出保单，Lloyd's 承保。出了事，真赔钱。卡住 AI 的不是能力，是没人敢担责。"    # ≤ 120 字符
SOURCE_URL = ""                                        # 原文链接，没有就留空

HTML_FILE  = PKG / "wechat.html"
COVER_FILE = PKG / "cover.jpg"


def die(msg):
    print(f"\n✗ {msg}\n")
    sys.exit(1)


def get_token(appid, secret):
    r = requests.get(f"{API}/token", params={
        "grant_type": "client_credential", "appid": appid, "secret": secret
    }, timeout=20).json()
    if "access_token" not in r:
        hint = ""
        if r.get("errcode") == 40164:
            hint = ("\n  这个错是 IP 不在白名单。去公众号后台 → 设置与开发 → 基本配置 →"
                    "\n  IP 白名单，把报错信息里那个 IP 加进去，等一分钟再跑。")
        die(f"拿不到 access_token：{r}{hint}")
    return r["access_token"]


def upload_cover(token, path):
    """封面要永久素材，返回 thumb_media_id"""
    with open(path, "rb") as f:
        r = requests.post(f"{API}/material/add_material",
                          params={"access_token": token, "type": "image"},
                          files={"media": (path.name, f, "image/jpeg")}, timeout=60).json()
    if "media_id" not in r:
        die(f"封面上传失败：{r}")
    print(f"  封面已上传 → media_id {r['media_id'][:16]}…")
    return r["media_id"]


def upload_inline(token, data: bytes, name: str):
    """正文配图，返回微信图片 URL"""
    r = requests.post(f"{API}/media/uploadimg",
                      params={"access_token": token},
                      files={"media": (name, io.BytesIO(data), "image/jpeg")}, timeout=60).json()
    if "url" not in r:
        die(f"正文配图上传失败：{r}")
    return r["url"]


def extract_body(html: str) -> str:
    """从打包页里取出真正要粘的正文（去掉工具条和脚本）"""
    m = re.search(r'<div class="paper" id="wx-content">(.*?)</div>\s*<script>', html, re.S)
    return m.group(1).strip() if m else html


def main():
    appid = os.environ.get("WECHAT_APPID")
    secret = os.environ.get("WECHAT_SECRET")
    if not appid or not secret:
        die("先设置环境变量：\n  export WECHAT_APPID=你的appid\n  export WECHAT_SECRET=你的secret")
    if not HTML_FILE.exists():
        die(f"找不到排版文件 {HTML_FILE}")

    print("1/4 换取 access_token …")
    token = get_token(appid, secret)

    print("2/4 上传封面 …")
    thumb_id = upload_cover(token, COVER_FILE)

    print("3/4 上传正文配图（微信不认 base64，必须逐张换成它自己的地址）…")
    body = extract_body(HTML_FILE.read_text(encoding="utf-8"))
    imgs = re.findall(r'src="data:image/(\w+);base64,([^"]+)"', body)
    print(f"  发现 {len(imgs)} 张内嵌图")
    for i, (ext, b64) in enumerate(imgs, 1):
        url = upload_inline(token, base64.b64decode(b64), f"img{i}.jpg")
        body = body.replace(f"data:image/{ext};base64,{b64}", url, 1)
        print(f"  {i}/{len(imgs)} → {url[:60]}…")

    print("4/4 创建草稿 …")
    payload = {"articles": [{
        "title": TITLE, "author": AUTHOR, "digest": DIGEST,
        "content": body, "content_source_url": SOURCE_URL,
        "thumb_media_id": thumb_id,
        "need_open_comment": 1, "only_fans_can_comment": 0,
    }]}
    r = requests.post(f"{API}/draft/add", params={"access_token": token},
                      data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                      timeout=60).json()
    if "media_id" not in r:
        die(f"建草稿失败：{r}")

    print(f"\n✓ 草稿已创建：{r['media_id']}")
    print("  去公众号后台 →「草稿箱」就能看到，排版和图片都在。")
    print("  留言已默认打开（这篇结尾要读者在评论区报数字，别关）。\n")


if __name__ == "__main__":
    main()

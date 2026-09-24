#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""公众号封面 v2：中央方形安全区 + 高对比底色。

为什么：微信订阅号消息里，次条/历史文章用 1:1 方形缩略图（约 108px）。
2.35:1 的横幅封面被居中裁切后，靠边的文字全被裁掉，浅底在信息流里等于隐形。
本生成器把核心文字压进中央 600x600 安全区，默认深色底。

用法：
  build_cover_v2.py --kicker "老登的自我救赎 01" --big "我把<em>流水线</em><br>开源了" \
     --sub "三套大号排版复刻器" [--theme dark|green|cream] [--art bg.png] [--out cover.jpg]
"""
import argparse, pathlib, subprocess, sys

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
W, H = 1410, 600
SQ = H
LEFT = (W - SQ) // 2

THEMES = {
    "dark":  dict(bg="#141416", fg="#ffffff", kc="#8f8f96", ac="#E5533C", art=".20"),
    "green": dict(bg="#123B2E", fg="#ffffff", kc="#9ec5b4", ac="#F2C14E", art=".22"),
    "cream": dict(bg="#F5F1E8", fg="#16161a", kc="#8a867f", ac="#C0392B", art=".85"),
}

TPL = """<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:{W}px;height:{H}px;background:{bg};position:relative;overflow:hidden;
 font-family:"PingFang SC",sans-serif}}
.art{{position:absolute;left:50%;bottom:-24px;transform:translateX(-50%);width:{W}px;opacity:{art}}}
.safe{{position:absolute;left:{LEFT}px;top:0;width:{SQ}px;height:{H}px;z-index:3;
 display:flex;flex-direction:column;justify-content:center;align-items:center;
 text-align:center;padding:0 30px}}
.k{{font-size:25px;color:{kc};letter-spacing:3px;font-weight:700;margin-bottom:20px}}
.big{{font-size:{bigsize}px;line-height:1.06;font-weight:900;color:{fg};letter-spacing:-3px}}
.big em{{font-style:normal;color:{ac}}}
.sub{{margin-top:20px;font-size:29px;color:{kc};font-weight:600}}
.rail{{position:absolute;left:0;top:0;bottom:0;width:12px;background:{ac};z-index:4}}
</style></head><body>{artimg}<div class="rail"></div>
<div class="safe"><div class="k">{kicker}</div><div class="big">{big}</div>{subdiv}</div>
</body></html>"""


def build(kicker, big, sub="", theme="dark", art=None, out="cover.jpg"):
    c = THEMES[theme]
    plain = big.replace("<br>", "").replace("<em>", "").replace("</em>", "")
    bigsize = 96 if len(plain) <= 12 else (80 if len(plain) <= 16 else 66)
    artimg = ('<img class="art" src="%s"/>' % pathlib.Path(art).resolve().as_uri()) if art else ""
    html = TPL.format(W=W, H=H, SQ=SQ, LEFT=LEFT, bigsize=bigsize, artimg=artimg,
                      kicker=kicker, big=big,
                      subdiv=('<div class="sub">%s</div>' % sub) if sub else "", **c)
    out = pathlib.Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    hp = out.with_suffix(".html"); hp.write_text(html, encoding="utf-8")
    png = out.with_suffix(".png")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    "--force-device-scale-factor=2", "--screenshot=%s" % png,
                    "--window-size=%d,%d" % (W, H), hp.resolve().as_uri()],
                   check=True, capture_output=True)
    subprocess.run(["sips", "-Z", "1410", "-s", "format", "jpeg", "-s", "formatOptions", "92",
                    str(png), "--out", str(out)], check=True, capture_output=True)
    print("✓ %s  1410x600 · 主题=%s · 中央方形安全区（缩略图可读）" % (out, theme))
    print("  ⚠️ 必须 Read 看一遍，并确认方形裁切后标题完整")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--kicker", required=True)
    ap.add_argument("--big", required=True, help="可用 <em> 标红、<br> 换行")
    ap.add_argument("--sub", default="")
    ap.add_argument("--theme", default="dark", choices=list(THEMES))
    ap.add_argument("--art", default=None)
    ap.add_argument("--out", default="cover.jpg")
    a = ap.parse_args()
    build(a.kicker, a.big, a.sub, a.theme, a.art, a.out)

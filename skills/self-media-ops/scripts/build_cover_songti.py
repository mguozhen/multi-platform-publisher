#!/usr/bin/env python3
"""生成公众号封面（2.35:1）。

三种版式，都用宋体——黑体大字是 AI 封面的标配长相，宋体自带编辑部气质。

用法：
    python3 build_cover.py --kicker "创业公司的" --title "Claude Code 使用秘籍" \
        --bg /path/to/abstract.png --layout band --out cover.jpg

版式（--layout）：
    plain  纯字，米白纸底，什么装饰都没有。最不可能被认成 AI 做的。
    band   背景图压成底部装饰带，上方留白放字。信息量最大，推荐。
    stack  标题拆两行 + 一个小红点收尾。字最大，信息流里最抢眼。

背景图要求（band 版式才需要）：
    抽象线条图，浅底深线，不要有文字。脚本会自动找出线条实际占据的行，
    裁成一条装饰带贴在画面底部，上方自动留白给标题。
"""
import argparse, os, pathlib, sys

try:
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np
except ImportError:
    sys.exit("缺依赖：pip3 install pillow numpy")

FONT_DIR = pathlib.Path.home() / "Library/Fonts"
SERIF = {                      # 思源宋体：编辑部气质，反 AI 味的关键
    "light":   "SourceHanSerifCN-Light.otf",
    "regular": "SourceHanSerifCN-Regular.otf",
    "bold":    "SourceHanSerifCN-Bold.otf",
}
PAPER = (250, 249, 246)
INK   = (22, 22, 22)
GREY  = (110, 105, 100)
RED   = (181, 80, 60)


SONGTI = "/System/Library/Fonts/Supplemental/Songti.ttc"
SONGTI_IDX = {"light": 3, "regular": 6, "bold": 1}   # Songti SC Light / Regular / Bold


def font(weight, size):
    p = FONT_DIR / SERIF[weight]
    if p.exists():
        return ImageFont.truetype(str(p), size)
    return ImageFont.truetype(SONGTI, size, index=SONGTI_IDX[weight])


def fit_size(draw, text, weight, max_width, start, floor=40):
    """标题太长就自动缩字号，直到塞得下"""
    size = start
    while size > floor and draw.textlength(text, font=font(weight, size)) > max_width:
        size -= 2
    return size


def line_band(bg_path, width, target_h=None):
    """从抽象背景图里切出线条实际占据的那一条。

    默认按宽度缩放（扁画布用）。给了 target_h 就改按高度缩放再横向居中裁切——
    画布一高，按宽度缩放会把线条压成底部一条细缝，必须按高度来。
    """
    src = Image.open(bg_path).convert("RGB")
    arr = np.asarray(src).astype(int)
    dark_rows = np.where((arr.sum(axis=2) < 600).any(axis=1))[0]
    if len(dark_rows) == 0:
        return None
    top = max(0, dark_rows[0] - 25)
    bottom = min(src.height, dark_rows[-1] + 25)
    band = src.crop((0, top, src.width, bottom))

    if target_h:
        w = round(band.width * target_h / band.height)
        band = band.resize((w, target_h), Image.LANCZOS)
        if w > width:                      # 太宽就居中裁
            x = (w - width) // 2
            band = band.crop((x, 0, x + width, target_h))
        elif w < width:                    # 太窄就贴在纸底上居中
            pad = Image.new("RGB", (width, target_h), PAPER)
            pad.paste(band, ((width - w) // 2, 0))
            band = pad
        return band
    return band.resize((width, round(band.height * width / band.width)), Image.LANCZOS)


def build(kicker, title, bg, layout, out, W=1410, H=600, kicker_size=None):
    canvas = Image.new("RGB", (W, H), PAPER)

    if layout == "band":
        if not bg:
            sys.exit("band 版式需要 --bg 指定背景图")
        src_ratio = Image.open(bg).height / Image.open(bg).width
        if src_ratio > 0.9:
            # 底图本身就是竖构图 → 整张铺满，别切成带子（切了边缘会露白色色差）
            art = Image.open(bg).convert("RGB")
            k = max(W / art.width, H / art.height)
            art = art.resize((round(art.width * k), round(art.height * k)), Image.LANCZOS)
            canvas.paste(art, (-(art.width - W) // 2, -(art.height - H) // 2))
        else:
            # 扁底图贴在下方；画布越高越要按高度撑，否则底部只剩一条缝
            band = line_band(bg, W, round(H * 0.42) if H / W > 0.6 else None)
            if band is None:
                sys.exit("背景图里没找到线条，换一张，或者改用 --layout plain")
            canvas.paste(band, (0, H - band.height))

    d = ImageDraw.Draw(canvas)
    pad = 96
    avail = W - pad * 2

    if layout == "stack":
        parts = title.split(" ", 1) if " " in title else [title]
        size = fit_size(d, max(parts, key=len), "bold", avail, 92)
        f_k, f_t = font("light", 54), font("bold", size)
        d.text((pad + 8, 92), kicker, font=f_k, fill=GREY)
        y = 178
        for i, p in enumerate(parts):
            d.text((pad + 4, y), p, font=f_t, fill=INK)
            if i == len(parts) - 1:
                w = d.textlength(p, font=f_t)
                cy = y + size * 0.62
                d.ellipse([pad + 4 + w + 34, cy, pad + 4 + w + 62, cy + 28], fill=RED)
            y += round(size * 1.35)
    else:
        big = 82 if layout == "band" else 104
        size = fit_size(d, title, "bold", avail, big)
        # kicker 不能太小，否则在信息流缩略图里根本看不见
        ks = kicker_size or (52 if layout == "band" else 56)
        f_k, f_t = font("regular", ks), font("bold", size)
        y = 66 if layout == "band" else 148
        d.text((pad, y), kicker, font=f_k, fill=GREY)
        d.text((pad - 4, y + round(ks * 1.45)), title, font=f_t, fill=INK)

    out = pathlib.Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, "JPEG", quality=93, optimize=True)
    print(f"✓ {out}  {W}x{H}  ({W/H:.2f}:1)  版式={layout}")
    print("  ⚠️ 必须用 Read 把这张图看一遍再交付——没看过截图 = 没验收")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--kicker", default="", help="标题上面那行小字")
    ap.add_argument("--title", required=True, help="封面主标题")
    ap.add_argument("--bg", help="抽象线条背景图（band 版式必需）")
    ap.add_argument("--layout", default="band", choices=["plain", "band", "stack"])
    ap.add_argument("--out", default="cover-2.35.jpg")
    ap.add_argument("--kicker-size", type=int, default=None,
                    help="上面那行小字的字号，不给用默认（band 52 / plain 56）")
    ap.add_argument("--width", type=int, default=1410)
    ap.add_argument("--height", type=int, default=600)
    a = ap.parse_args()
    build(a.kicker, a.title, a.bg, a.layout, a.out, a.width, a.height, a.kicker_size)


# ---------------------------------------------------------------------------
# hunter 版式：仿 Agent101 / Hunter 的工业风封面
# 取自其真实封面实测：黑体 + 砖红 accent + 左侧红竖线 + 右上角红框徽章
# ---------------------------------------------------------------------------
SANS = {                       # 注意本机文件名带 #1 后缀
    "bold":    "SourceHanSansCN-Bold#1.otf",
    "medium":  "SourceHanSansCN-Medium#1.otf",
    "regular": "SourceHanSansCN-Regular#1.otf",
}
HB_BG    = (246, 246, 244)   # 底色
HB_INK   = (26, 26, 26)      # 标题黑
HB_RED   = (200, 62, 52)     # 主 accent
HB_GREY  = (95, 95, 92)      # 说明文字
HB_FAINT = (150, 150, 146)   # 底部署名


def sans(weight, size):
    p = FONT_DIR / SANS[weight]
    if not p.exists():
        sys.exit(f"找不到字体 {p}（需要思源黑体 SourceHanSansCN）")
    return ImageFont.truetype(str(p), size)


def build_hunter(kicker, title, subtitle, note, badge, byline, out, W=1010, H=600):
    """kicker  顶部红色小字，用 / 分隔，如「团队知识 / 深度洞察」
       title   主标题（黑）
       subtitle 副标题（红），可为空
       note    说明文字，\n 换行
       badge   右上角徽章文字，如「实测 · 580 行」
       byline  底部署名
    """
    c = Image.new("RGB", (W, H), HB_BG)
    d = ImageDraw.Draw(c)

    s = W / 1279.0                      # 字号/横向按宽度缩放
    L = round(84 * s)                   # 左边距
    d.rectangle([0, 0, round(7 * s), H], fill=HB_RED)   # 左侧红竖线，通高

    # 纵向按实测原图的比例走（原图 1279x544），不跟着宽度缩，否则上半部会挤成一团
    y_kicker = round(0.081 * H)
    y_title  = round(0.175 * H)

    f_k = sans("medium", max(13, round(21 * s)))
    d.text((L, y_kicker), kicker, font=f_k, fill=HB_RED)

    if badge:                                            # 右上角红框徽章
        f_b = sans("medium", max(11, round(18 * s)))
        tw = d.textlength(badge, font=f_b)
        bh, px = round(36 * s), round(16 * s)
        bx1 = W - round(64 * s); bx0 = bx1 - tw - px * 2
        by0 = y_kicker - round(7 * s)
        d.rounded_rectangle([bx0, by0, bx1, by0 + bh], radius=round(5 * s),
                            outline=HB_RED, width=max(1, round(1.6 * s)))
        d.text((bx0 + px, by0 + round(9 * s)), badge, font=f_b, fill=HB_RED)

    avail = W - L - round(120 * s)
    ts = round(48 * s)
    while ts > 20 and max(d.textlength(title, font=sans("bold", ts)),
                          d.textlength(subtitle or "", font=sans("bold", ts))) > avail:
        ts -= 1
    f_t = sans("bold", ts)

    y = y_title
    d.text((L, y), title, font=f_t, fill=HB_INK)
    if subtitle:
        y += round(ts * 1.30)
        d.text((L, y), subtitle, font=f_t, fill=HB_RED)

    if note:
        f_n = sans("regular", max(12, round(19 * s)))
        y += round(ts * 1.62)                            # 说明文字跟标题拉开
        for ln in note.split("\n"):
            d.text((L, y), ln, font=f_n, fill=HB_GREY)
            y += round(31 * s)

    if byline:
        f_by = sans("regular", max(11, round(17 * s)))
        d.text((L, round(H * 0.895)), byline, font=f_by, fill=HB_FAINT)

    out = pathlib.Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    c.save(out, "JPEG", quality=94, optimize=True)
    print(f"✓ {out}  {W}x{H}  ({W/H:.2f}:1)  版式=hunter")
    print("  ⚠️ 必须 Read 看一遍再交付")

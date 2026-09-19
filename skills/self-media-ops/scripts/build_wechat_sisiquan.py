#!/usr/bin/env python3
"""article.md → 公众号 HTML（复刻「深思圈」排版）

排版参数全部从深思圈原文的内联样式里量出来：
  字体     Optima-Regular, PingFangTC-light   （全文唯一字体，49 处）
  正文     line-height:2  padding:0 16px  左对齐，不设 font-size（继承微信默认）
  小标题   font-size:28px  color:rgb(0,0,0)  <strong>  同样 padding:0 16px
  段间距   靠空的 <p><br></p> 制造；小标题前两个，后一个
  零色块、零装饰线、零引用框
"""
import base64, mimetypes, pathlib, re, sys

SRC = pathlib.Path("article.md")
OUT = pathlib.Path("wechat.html")

FONT = "Optima-Regular, PingFangTC-light"
WRAP_O = '<section style=" max-width: 100%;  box-sizing: border-box; ">'
BODY_S = ('<section style="text-align: left; font-family: %s; line-height: 2; '
          'padding: 0px 16px; box-sizing: border-box; max-width: 100%%;">' % FONT)
HEAD_S = ('<section style="text-align: left; font-size: 28px; color: rgb(0, 0, 0); '
          'padding: 0px 16px; font-family: %s; box-sizing: border-box; max-width: 100%%;">' % FONT)
P_S    = '<p style="margin: 0px; padding: 0px; box-sizing: border-box;">'
BLANK  = ('<p style="white-space: normal; margin: 0px; padding: 0px; box-sizing: border-box;">'
          '<span leaf=""><br  /></span></p>')


def b64(path):
    p = pathlib.Path(path)
    if not p.exists():
        sys.exit(f"找不到图片 {p}")
    mime = mimetypes.guess_type(p.name)[0] or "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


def inline(t):
    """**加粗** → 深思圈的 <strong><span leaf=""> 结构"""
    t = (t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    t = re.sub(r"\*\*(.+?)\*\*",
               r'</span><strong style="box-sizing: border-box;"><span leaf="">\1</span></strong><span leaf="">',
               t)
    return t


def para(text):
    return WRAP_O + BODY_S + P_S + '<span leaf="">' + inline(text) + "</span></p></section></section>"


def heading(text):
    return (WRAP_O + HEAD_S + P_S + '<strong style="box-sizing: border-box;">'
            '<span leaf="">' + inline(text) + "</span></strong></p></section></section>")


def image(src):
    return (WRAP_O + BODY_S + P_S + '<img src="%s" style="max-width:100%%; width:100%%; '
            'height:auto; display:block; box-sizing:border-box;" />' % b64(src)
            + "</p></section></section>")


def main():
    md = SRC.read_text(encoding="utf-8").split("\n")
    out, n = [], 0
    for raw in md:
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.startswith("# "):                       # 文章大标题不进正文
            continue
        if line.startswith("## "):
            n += 1
            out.append(BLANK); out.append(BLANK)
            out.append(para("%02d" % n))                # 编号单独一段，跟深思圈一致
            out.append(BLANK)
            out.append(heading(line[3:].strip()))
            out.append(BLANK)
            continue
        m = re.match(r"!\[[^\]]*\]\(([^)]+)\)", line)
        if m:
            out.append(image(m.group(1))); out.append(BLANK); continue
        if line.strip() == "---":
            out.append(BLANK); continue
        out.append(para(line.strip())); out.append(BLANK)

    html = ('<div style="background:#ffffff; font-family:%s;">' % FONT) + "".join(out) + "</div>"
    OUT.write_text(html, encoding="utf-8")
    words = len(re.sub(r"\s", "", re.sub(r"<[^>]+>", "", html)))
    print(f"✓ {OUT}  {len(html)//1024} KB  · 小节 {n} 个 · 复刻深思圈排版")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""article.md → 公众号 HTML（复刻「晚点再听LaterCast」排版系统）
数值实测见 ~/self-media/playbooks/wechat-latepost-playbook.md
  正文 16px lh2em mb20px 系统字体栈 | 黄 rgb(252,220,112)
  H2 22px/600 居中黄底荧光 | ==引语==→黄底斜体 | > →黄左条引用块
  图注 12px rgba(0,0,0,.5) 居中 | %% →14px 栏目导语 | --- 后→灰小字
用法: build_wechat_latepost.py article.md [out.html]
"""
import base64, mimetypes, pathlib, re, sys

Y = "rgb(252, 220, 112)"
FONT = ("-apple-system, BlinkMacSystemFont, 'PingFang SC', 'Helvetica Neue', "
        "'Microsoft YaHei', sans-serif")
P = ('<p style="font-family: %s;font-size: 16px;margin-bottom: 20px;'
     'line-height: 2em;text-align: left;">%%s</p>' % FONT)
H2 = ('<h2 style="font-family: %s;margin: 40px 0px 20px;font-size: 22px;'
      'font-weight: 600;line-height: 1.6em;text-align: center;">'
      '<span style="background-color: %s;">%%s</span></h2>' % (FONT, Y))
QUOTE = ('<p style="font-family: %s;font-size: 15px;color: rgb(85, 85, 85);'
         'border-left: 4px solid %s;padding-left: 12px;margin: 24px 0px;'
         'font-style: italic;background: rgb(255, 255, 255);line-height: 2em;'
         'text-align: left;">%%s</p>' % (FONT, Y))
INTRO = ('<p style="font-family: %s;font-size: 14px;color: rgba(0, 0, 0, 0.6);'
         'line-height: 1.75em;text-align: left;margin-bottom: 20px;">%%s</p>' % FONT)
CAP = ('<p style="font-family: %s;font-size: 12px;line-height: 1.6em;'
       'text-align: center;color: rgba(0, 0, 0, 0.5);margin: 8px 0 24px;">%%s</p>' % FONT)
SMALL = ('<p style="font-family: %s;font-size: 13px;color: rgba(0, 0, 0, 0.45);'
         'line-height: 1.8em;text-align: left;margin: 12px 0;">%%s</p>' % FONT)
IMG = ('<p style="text-align:center;margin: 24px 0 0;">'
       '<img src="%s" style="max-width:100%%;border-radius:2px;" /></p>')

def esc(t):
    return t.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

def inline(t):
    t = esc(t)
    t = re.sub(r'==(.+?)==',
        r'<span style="background-color: %s;font-style: italic;">\1</span>' % Y, t)
    t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
    return t

def img_tag(path, root):
    p = root / path
    if p.exists():
        mime = mimetypes.guess_type(str(p))[0] or 'image/jpeg'
        return IMG % ('data:%s;base64,%s' % (mime, base64.b64encode(p.read_bytes()).decode()))
    return IMG % path

def build(src, out=None):
    src = pathlib.Path(src); root = src.parent
    lines = src.read_text(encoding='utf-8').split('\n')
    o, i, title, small = [], 0, '', False
    while i < len(lines):
        ln = lines[i].rstrip()
        if ln.startswith('# ') and not title:
            title = ln[2:].strip(); i += 1; continue
        if ln == '---':
            small = True
            o.append(P % ('如果这篇对你有用，<strong>关注「Agent101」</strong>，每天一篇硅谷前沿 AI 观察。'))
            i += 1; continue
        if ln.startswith('%% '):
            o.append(INTRO % inline(ln[3:])); i += 1; continue
        if ln.startswith('## '):
            o.append(H2 % inline(ln[3:])); i += 1; continue
        if ln.startswith('> '):
            o.append(QUOTE % inline(ln[2:])); i += 1; continue
        m = re.match(r'!\[[^\]]*\]\(([^)]+)\)', ln)
        if m:
            o.append(img_tag(m.group(1), root))
            if i+1 < len(lines):
                cm = re.match(r'^\*([^*].*?)\*$', lines[i+1].strip())
                if cm: o.append(CAP % esc(cm.group(1))); i += 1
            i += 1; continue
        if ln.strip():
            o.append((SMALL if small else P) % inline(ln.strip()))
        i += 1
    html = ('<section style="font-size: 16px;background-color: rgb(255, 255, 255);">%s'
            '</section>') % '\n'.join(o)
    outp = pathlib.Path(out) if out else src.with_name('wechat.html')
    outp.write_text(html, encoding='utf-8')
    print('✓ %s  %d KB · H2 %d · 黄底引语 %d · 引用块 %d · 复刻晚点排版' % (
        outp.name, len(html)//1024, html.count('<h2'),
        html.count('font-style: italic;">')-html.count('border-left'),
        html.count('border-left')))
    return outp

if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)

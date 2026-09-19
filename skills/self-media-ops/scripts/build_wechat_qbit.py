#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""article.md → 公众号 HTML（复刻「量子位」排版系统）
数值全部从量子位原文 inline style 量出，见 ~/self-media/playbooks/wechat-qbit-playbook.md
  正文  16px #222 Arial lh2 ls1px margin 20px 16px
  高亮  <strong> 绿 rgb(0,153,127) 加粗
  H2   20px bold 绿左竖条 6px padding-left 15px margin 40px 0
  图注  14px #888 居中
  尾部  绿渐变条(rotateY 180) + 右对齐一键三连
用法: build_wechat_qbit.py article.md [out.html]
"""
import base64, mimetypes, pathlib, re, sys

GREEN = "rgb(0, 153, 127)"
P = ('<p style="color: rgb(34, 34, 34);font-size: 16px;font-family: Arial;'
     'text-align: left;letter-spacing: 1px;word-spacing: 1px;line-height: 2;'
     'margin: 20px 16px;">%s</p>')
H2 = ('<h2 style="color: rgb(34, 34, 34);font-family: Arial, Helvetica, sans-serif;'
      'text-align: left;margin: 40px 16px;line-height: 1.5;font-weight: bold;'
      'padding-left: 15px;border-left: 6px solid %s;font-size: 20px;'
      'letter-spacing: 1px;word-spacing: 1px;"><span>%s</span></h2>' % (GREEN, "%s"))
CAP = ('<p style="text-align: center;font-size: 14px;color: rgb(136, 136, 136);'
       'margin: 0 16px 20px;">%s</p>')
SMALL = ('<p style="color: rgb(136, 136, 136);font-size: 14px;font-family: Arial;'
         'letter-spacing: 1px;line-height: 1.8;margin: 12px 16px;">%s</p>')
IMG = ('<p style="text-align:center;margin: 20px 0 8px;">'
       '<img src="%s" style="margin: 0px auto;padding: 0px;max-width:100%%;'
       'border-radius:4px;" /></p>')
DIVIDER = ('<section style="transform: perspective(0px);transform-style: flat;">'
  '<section style="margin-top: 30px;margin-bottom: 10px;transform: rotateY(180deg);">'
  '<section style="width: 100%%;height: 5px;background-image: linear-gradient(90deg, '
  'rgba(0, 153, 127, 0.5) 13%%, rgba(235, 25, 24, 0) 100%%);"></section></section></section>')
TAIL = (DIVIDER +
  '<p style="text-align: right;margin: 20px 16px;font-size: 16px;font-family: Arial;">'
  '<strong>一键三连</strong><span style="color: %s;"><strong>「点赞」「转发」「小心心」</strong></span></p>'
  '<p style="text-align: right;margin: 10px 16px 30px;font-size: 16px;font-family: Arial;">'
  '<strong>欢迎在评论区留下你的想法！</strong></p>') % GREEN

def esc(t):
    return t.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

def inline(t):
    t = esc(t)
    t = re.sub(r'\*\*(.+?)\*\*',
        r'<strong><span style="font-weight: bold;color: %s;">\1</span></strong>' % GREEN, t)
    return t

def img_tag(path, root):
    p = (root / path)
    if p.exists():
        mime = mimetypes.guess_type(str(p))[0] or 'image/jpeg'
        b64 = base64.b64encode(p.read_bytes()).decode()
        return IMG % ('data:%s;base64,%s' % (mime, b64))
    return IMG % path

def build(src, out=None):
    src = pathlib.Path(src); root = src.parent
    lines = src.read_text(encoding='utf-8').split('\n')
    o, i, title, in_small = [], 0, '', False
    # 头部署名（量子位式两行）
    o.append('<p style="text-align: left;margin: 20px 16px 4px;font-size: 14px;'
             'color: rgb(136, 136, 136);font-family: Arial;">Hunter 发自 圣何塞</p>')
    o.append('<p style="text-align: left;margin: 0 16px 10px;font-size: 14px;'
             'color: %s;font-family: Arial;">Hunter 在跑 | 硅谷前沿 AI 观察</p>' % GREEN)
    while i < len(lines):
        ln = lines[i].rstrip()
        if ln.startswith('# ') and not title:
            title = ln[2:].strip(); i += 1; continue
        if ln == '---':
            in_small = True; o.append(TAIL); i += 1; continue
        if ln.startswith('## '):
            o.append(H2 % inline(ln[3:])); i += 1; continue
        m = re.match(r'!\[[^\]]*\]\(([^)]+)\)', ln)
        if m:
            o.append(img_tag(m.group(1), root))
            if i+1 < len(lines):
                cm = re.match(r'^\*([^*]+)\*$', lines[i+1].strip())
                if cm: o.append(CAP % esc(cm.group(1))); i += 1
            i += 1; continue
        if ln.strip():
            o.append((SMALL if in_small else P) % inline(ln.strip()))
        i += 1
    html = ('<section style="font-size: 16px;color: rgb(34, 34, 34);'
            'background-color: rgb(255, 255, 255);">%s</section>') % '\n'.join(o)
    outp = pathlib.Path(out) if out else src.with_name('wechat.html')
    outp.write_text(html, encoding='utf-8')
    n_hl = html.count('color: %s;">' % GREEN)
    print('✓ %s  %d KB · H2 %d 个 · 绿色高亮≈%d 处 · 复刻量子位排版' %
          (outp.name, len(html)//1024, html.count('<h2'), html.count('font-weight: bold;color:')))
    return outp

if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)

"""
全平台预览页 — 把一次抽卡生成的多平台内容渲染成一个网页，部署到 Vercel。

  build_and_deploy(card, drafts, wx_result) -> {url, local_path}
    card       抽到的选题卡 dict
    drafts     {platform: draft_entry}  非公众号的 5 个平台
    wx_result  公众号草稿箱推送结果 {ok, media_id|error}

部署策略:
  固定目录 ~/self-media/preview-site/ 作为 Vercel 项目根，
  .vercel/ 链接持久化 → 每次抽卡生成一个独立 preview URL (历史保留)。

前置:
  vercel CLI 已登录 (`vercel login`)。Hunter 的 btcmind.ai 已在 Vercel，应已登录。
"""
from __future__ import annotations

import html
import subprocess
import time
from pathlib import Path

HOME = Path.home()
SELF_MEDIA = HOME / "self-media"
DEPLOY_DIR = SELF_MEDIA / "preview-site"

PLATFORM_META = {
    "x":           ("𝕏",  "X / Twitter",  "推文 — 复制即发"),
    "linkedin":    ("in", "LinkedIn",     "Founder 自白长贴"),
    "xiaohongshu": ("📕", "小红书",        "图文 — 标题钩子 + emoji"),
    "douyin":      ("🎵", "抖音",          "口播脚本 + 分镜"),
    "tiktok":      ("🎬", "TikTok",        "英文口播脚本 + 分镜"),
}
ORDER = ["x", "linkedin", "xiaohongshu", "douyin", "tiktok"]


def _esc(s: str) -> str:
    return html.escape(s or "", quote=True)


def build_html(card: dict, drafts: dict, wx_result: dict) -> str:
    title = _esc(card.get("title", "未命名选题"))
    src = _esc(card.get("source", ""))
    ts = time.strftime("%Y-%m-%d %H:%M")

    if wx_result.get("ok"):
        wx_html = ('<div class="wx ok">✅ 公众号草稿箱已推送 — '
                   '去微信公众平台「草稿箱」验证排版后发布</div>')
    else:
        wx_html = ('<div class="wx err">⚠️ 公众号草稿推送失败：'
                   f'{_esc(wx_result.get("error", "unknown"))}</div>')

    cards = []
    for p in ORDER:
        d = drafts.get(p)
        if not d:
            continue
        emoji, name, sub = PLATFORM_META[p]
        body = _esc(d.get("draft_text", ""))
        cards.append(f"""
    <section class="card" data-p="{p}">
      <div class="chead">
        <span class="badge">{emoji}</span>
        <div><h2>{_esc(name)}</h2><p class="sub">{_esc(sub)}</p></div>
        <button class="copy" onclick="cp(this)">复制</button>
      </div>
      <pre class="body">{body}</pre>
    </section>""")

    return f"""<!doctype html>
<html lang="zh"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex">
<title>全平台预览 · {title}</title>
<style>
  :root {{ color-scheme: dark; }}
  * {{ box-sizing: border-box; margin: 0; }}
  body {{ background:#0d0d10; color:#e8e8ea; font:15px/1.6 -apple-system,
          "PingFang SC",Segoe UI,sans-serif; padding:24px 16px 64px; }}
  .wrap {{ max-width: 720px; margin: 0 auto; }}
  header {{ margin-bottom: 20px; }}
  h1 {{ font-size: 20px; line-height:1.4; }}
  .meta {{ color:#7c7c85; font-size:13px; margin-top:6px; }}
  .wx {{ margin:16px 0; padding:12px 14px; border-radius:10px; font-size:14px; }}
  .wx.ok {{ background:#11301c; color:#7ee2a8; }}
  .wx.err {{ background:#3a1414; color:#f0a0a0; }}
  .card {{ background:#16161b; border:1px solid #26262e; border-radius:14px;
           margin-bottom:16px; overflow:hidden; }}
  .chead {{ display:flex; align-items:center; gap:12px; padding:14px 16px;
            border-bottom:1px solid #26262e; }}
  .badge {{ width:34px; height:34px; flex:none; display:flex; align-items:center;
            justify-content:center; background:#23232c; border-radius:9px;
            font-size:16px; }}
  .chead h2 {{ font-size:15px; }}
  .sub {{ color:#7c7c85; font-size:12px; }}
  .copy {{ margin-left:auto; background:#2b2b36; color:#cfcfd6; border:0;
           padding:7px 14px; border-radius:8px; font-size:13px; cursor:pointer; }}
  .copy:active {{ background:#3a3a48; }}
  .body {{ padding:16px; white-space:pre-wrap; word-break:break-word;
           font:14px/1.7 ui-monospace,SFMono-Regular,Menlo,monospace; }}
  footer {{ color:#5a5a63; font-size:12px; text-align:center; margin-top:32px; }}
</style></head><body>
<div class="wrap">
  <header>
    <h1>🌐 {title}</h1>
    <p class="meta">来源 {src} · 生成于 {ts} · 看完逐平台在 Telegram 确认发布</p>
  </header>
  {wx_html}
  {''.join(cards)}
  <footer>self-media 抽卡引擎 · 全平台预览</footer>
</div>
<script>
function cp(btn) {{
  const t = btn.closest('.card').querySelector('.body').innerText;
  navigator.clipboard.writeText(t).then(() => {{
    const o = btn.textContent; btn.textContent = '已复制 ✓';
    setTimeout(() => btn.textContent = o, 1500);
  }});
}}
</script>
</body></html>"""


def _vercel_bin() -> str:
    """Resolve the vercel CLI — PATH first, then known npm-global locations."""
    from shutil import which
    found = which("vercel")
    if found:
        return found
    for cand in (HOME / ".hermes/node/bin/vercel",
                 Path("/opt/homebrew/bin/vercel"),
                 Path("/usr/local/bin/vercel")):
        if cand.exists():
            return str(cand)
    raise RuntimeError("vercel CLI 未找到 (npm i -g vercel)")


def _deploy(deploy_dir: Path) -> str:
    """vercel deploy → 返回 preview URL。失败抛 RuntimeError。"""
    try:
        out = subprocess.run(
            [_vercel_bin(), "deploy", "--yes"],
            cwd=str(deploy_dir), capture_output=True, text=True, timeout=180,
        )
    except FileNotFoundError as e:
        raise RuntimeError("vercel CLI 未安装 (npm i -g vercel)") from e
    except subprocess.TimeoutExpired as e:
        raise RuntimeError("vercel deploy 超时 (>180s)") from e
    blob = (out.stdout or "") + "\n" + (out.stderr or "")
    url = next((tok for ln in blob.splitlines()
                for tok in ln.split()
                if tok.startswith("https://") and "vercel.app" in tok), "")
    if not url:
        raise RuntimeError(f"vercel 没返回 URL: {blob.strip()[-300:]}")
    return url


def build_and_deploy(card: dict, drafts: dict, wx_result: dict) -> dict:
    """渲染 + 部署。返回 {url, local_path}; url 为 None 表示部署失败。"""
    DEPLOY_DIR.mkdir(parents=True, exist_ok=True)
    index = DEPLOY_DIR / "index.html"
    index.write_text(build_html(card, drafts, wx_result), encoding="utf-8")
    try:
        url = _deploy(DEPLOY_DIR)
    except RuntimeError as e:
        return {"url": None, "local_path": str(index), "error": str(e)}
    return {"url": url, "local_path": str(index)}

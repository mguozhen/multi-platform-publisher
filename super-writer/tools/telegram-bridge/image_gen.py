"""
配图生成 — Nano Banana (gemini-2.5-flash-image) via flatkey router。

  generate_image(prompt, out_path, size="...") -> Path
  cover_prompt(title, platform) -> str          平台封面的英文 prompt

Nano Banana 是 Gemini 多模态模型，走 **chat completions** 出图（不是 images
endpoint）。返回里 message.images[0].image_url.url 是 data:image/...;base64,。

策略: 先 IMAGE_MODEL，失败用 IMAGE_FALLBACK_MODEL，同一个 key。

ENV (telegram-bridge/.env，自动加载):
  IMAGE_API_KEY        flatkey router 的图像 key
  IMAGE_BASE_URL       默认 https://router.flatkey.ai/v1
  IMAGE_MODEL          默认 gemini-2.5-flash-image (nano banana)
  IMAGE_FALLBACK_MODEL 默认 gemini-3-pro-image-preview

尺寸: 模型不收 size 参数，靠 prompt 里的构图描述控制宽高比 (cover_prompt 已带)。

CLI
  python3 image_gen.py "a prompt" out.png
"""
from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

HOME = Path.home()

# 所有生成的图都归档到这里，作为写文章的素材库
ASSET_DIR = HOME / "self-media" / "assets" / "images"
ASSET_INDEX = ASSET_DIR / "index.jsonl"


def _load_bridge_env() -> None:
    env_file = Path(__file__).resolve().parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _extract_image(msg) -> bytes | None:
    """从 chat message 的 images 字段取出图片字节。"""
    imgs = getattr(msg, "images", None) or []
    for it in imgs:
        d = it if isinstance(it, dict) else (
            it.model_dump() if hasattr(it, "model_dump") else {})
        url = (d.get("image_url") or {}).get("url", "")
        if url.startswith("data:"):
            return base64.b64decode(url.split(",", 1)[1])
        if url.startswith("http"):
            with urllib.request.urlopen(url, timeout=120) as r:
                return r.read()
    return None


def _gen_one(base: str, key: str, model: str, prompt: str) -> bytes:
    """chat completions 出图，返回图片字节。失败抛 RuntimeError。"""
    try:
        from openai import OpenAI
    except ImportError as e:
        raise RuntimeError("缺少 openai SDK (pip install openai)") from e
    client = OpenAI(api_key=key, base_url=base) if base else OpenAI(api_key=key)
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
        )
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"{type(e).__name__}: {str(e)[:200]}") from e
    img = _extract_image(resp.choices[0].message)
    if img is None:
        raise RuntimeError(f"{model} 响应里没有图片")
    return img


# ───────────────────── 素材库归档 ─────────────────────────
def _archive(img: bytes, prompt: str, model: str) -> Path:
    """把生成的图归档进素材库，并往 index.jsonl 记一条元数据。"""
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    h = hashlib.md5(img).hexdigest()[:6]
    fname = f"{time.strftime('%Y%m%d-%H%M%S')}-{h}.png"
    (ASSET_DIR / fname).write_bytes(img)
    rec = {
        "file": fname,
        "prompt": prompt,
        "model": model,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "bytes": len(img),
    }
    with ASSET_INDEX.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    try:
        build_gallery()                     # 每次归档刷新画廊
    except Exception:  # noqa: BLE001
        pass
    return ASSET_DIR / fname


def build_gallery() -> Path:
    """从 index.jsonl 生成 gallery.html — 写文章时翻素材用。"""
    recs = []
    if ASSET_INDEX.exists():
        for ln in ASSET_INDEX.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                try:
                    recs.append(json.loads(ln))
                except json.JSONDecodeError:
                    pass
    recs.reverse()
    cards = "".join(
        f'<figure><a href="{html.escape(r["file"])}" target="_blank">'
        f'<img src="{html.escape(r["file"])}" loading="lazy"></a>'
        f'<figcaption>{html.escape(r.get("prompt", ""))}'
        f'<span>{html.escape(r.get("model", ""))} · '
        f'{html.escape(r.get("created_at", ""))}</span></figcaption></figure>'
        for r in recs)
    page = (
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>图片素材库 · {len(recs)} 张</title><style>'
        'body{background:#0d0d10;color:#e8e8ea;font:14px/1.5 -apple-system,'
        '"PingFang SC",sans-serif;margin:0;padding:24px}'
        'h1{font-size:18px;margin:0 0 16px}'
        '.grid{display:grid;grid-template-columns:repeat(auto-fill,'
        'minmax(220px,1fr));gap:16px}'
        'figure{margin:0;background:#16161b;border:1px solid #26262e;'
        'border-radius:10px;overflow:hidden}'
        'img{width:100%;display:block;aspect-ratio:1;object-fit:cover}'
        'figcaption{padding:10px;font-size:12px;color:#c8c8cf}'
        'figcaption span{display:block;margin-top:6px;color:#6c6c75;'
        'font-size:11px}'
        f'</style></head><body><h1>🖼 图片素材库 — {len(recs)} 张</h1>'
        f'<div class="grid">{cards}</div></body></html>')
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    out = ASSET_DIR / "gallery.html"
    out.write_text(page, encoding="utf-8")
    return out


# ───────────────────── public API ───────────────────────
def generate_image(prompt: str, out_path, size: str = "1536x1024") -> Path:
    """生成一张图存到 out_path，并归档进素材库。

    主走 IMAGE_MODEL，失败兜底 IMAGE_FALLBACK_MODEL。
    size 仅用于挑选 cover_prompt 的构图措辞，不直接传给模型。
    """
    _load_bridge_env()
    out = Path(out_path).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)

    base = os.environ.get("IMAGE_BASE_URL", "https://router.flatkey.ai/v1")
    key = os.environ.get("IMAGE_API_KEY") or os.environ.get("LLM_API_KEY", "")
    primary = os.environ.get("IMAGE_MODEL", "gemini-2.5-flash-image")
    fallback = os.environ.get("IMAGE_FALLBACK_MODEL", "gemini-3-pro-image-preview")
    if not key:
        raise RuntimeError("缺少 IMAGE_API_KEY (写进 .env)")

    errors = []
    for model in (primary, fallback):
        if not model:
            continue
        try:
            img = _gen_one(base, key, model, prompt)
        except RuntimeError as e:
            errors.append(f"{model}: {e}")
            continue
        out.write_bytes(img)
        _archive(img, prompt, model)        # 每张都进素材库
        return out
    raise RuntimeError("图像生成全部失败 — " + " | ".join(errors))


def cover_prompt(title: str, platform: str) -> str:
    """根据标题 + 平台生成封面图的英文 prompt。图像模型不擅长出文字，禁文字。"""
    base = (f'Editorial cover illustration about the concept: "{title}". '
            "Modern, clean, conceptual. No text, no words, no letters. ")
    style = {
        "wechat":   "Dark moody tech-editorial style, abstract geometric, "
                    "cinematic lighting, wide 16:9 composition.",
        "linkedin": "Professional minimalist tech style, soft gradient, "
                    "abstract, calm confident tone, wide 16:9 composition.",
        "xiaohongshu": "Bright vivid eye-catching style, warm colors, "
                       "playful flat illustration, tall vertical 3:4 composition.",
    }.get(platform, "Clean minimalist abstract style.")
    return base + style


# ─────────────────────── cli ────────────────────────────
def main() -> None:
    args = sys.argv[1:]
    if args and args[0] == "--gallery":
        g = build_gallery()
        print(f"✅ 素材库画廊 → {g}")
        return
    if len(args) < 2:
        print('用法: python3 image_gen.py "prompt" out.png')
        print("      python3 image_gen.py --gallery   重建素材库画廊")
        sys.exit(1)
    try:
        p = generate_image(args[0], args[1])
        print(f"✅ 图片已生成 → {p} ({p.stat().st_size} bytes)")
    except RuntimeError as e:
        sys.exit(f"❌ {e}")


if __name__ == "__main__":
    main()

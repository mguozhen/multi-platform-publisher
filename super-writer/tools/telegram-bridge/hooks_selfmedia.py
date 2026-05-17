"""
self-media hooks — real integration for Hunter's 6-platform posting.

generate(entry) — draft a post via LLM, loading the chosen platform playbook
                  + rejection_reasons as "AVOID THIS" negative examples.
execute(entry)  — publish to entry["context"]["platform"].

entry["context"] shape (set by bridge.py handle_playbook):
  {
    "platform": "wechat|x|linkedin|xiaohongshu|douyin|tiktok",
    "topic":    "选题一句话",
    "rationale": "为什么这条值得发",
    "playbook_variant": "A — build 推文 ...",
    "source_ref": "...",
    "full_content": "inbox 投喂的全文 (如有)",
  }

Platforms:
  wechat    → stage markdown to file (mdnice 手动排版)
  x         → stage to file (手贴 / X API 后续)
  linkedin  → li-post.py (needs ~/.secrets/linkedin.env)
  xiaohongshu → xhs-mcp CLI (working)
  douyin    → autopost.video 视频链路 (stage spec, video gen 二次 approve)
  tiktok    → autopost.video translate_dub + humanize
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

HOME = Path.home()
SELF_MEDIA = HOME / "self-media"
PLAYBOOKS = SELF_MEDIA / "playbooks"
STAGE = SELF_MEDIA / "content" / "_staged"


# ───────────────────────── generate ─────────────────────────
def generate(entry: dict) -> str:
    ctx = entry.get("context", {})
    platform = ctx.get("platform", "x")
    topic = ctx.get("topic", "")
    variant = ctx.get("playbook_variant", "")
    rationale = ctx.get("rationale", "")
    full = ctx.get("full_content", "")
    reasons = entry.get("rejection_reasons", [])

    playbook = _read(PLAYBOOKS / f"{platform}.md", limit=8000)
    persona = _read(SELF_MEDIA / "persona.md", limit=1500)

    avoid = ""
    if reasons:
        avoid = "\n\nAVOID THIS — earlier drafts were rejected because:\n" + \
            "\n".join(f"  {i}. {r}" for i, r in enumerate(reasons, 1))

    is_video = platform in ("douyin", "tiktok")
    output_kind = "视频口播脚本 + 分镜" if is_video else "帖子正文"
    material = ("素材全文:\n" + full) if full else ""

    prompt = "\n".join([
        f"你在为 Hunter 写一条 {platform} 内容。",
        "",
        f"选题: {topic}",
        f"为什么发: {rationale}",
        material,
        "",
        "用这个 playbook，并严格遵守选定的 variant:",
        f"=== PLAYBOOK ({platform}) ===",
        playbook,
        "=== 选定 variant ===",
        variant,
        "",
        "Hunter persona (语气锚):",
        persona,
        avoid,
        "",
        f"只输出{output_kind}本身。不要前言、不要解释、不要客套。",
    ])

    return _llm(prompt).strip()


# ───────────────────────── execute ──────────────────────────
def execute(entry: dict) -> dict:
    platform = entry.get("context", {}).get("platform", "x")
    text = entry["draft_text"]
    dispatch = {
        "wechat": _exec_wechat,
        "x": _exec_x,
        "linkedin": _exec_linkedin,
        "xiaohongshu": _exec_xhs,
        "douyin": _exec_video,
        "tiktok": _exec_video,
    }
    fn = dispatch.get(platform)
    if not fn:
        return {"ok": False, "error": f"unknown platform: {platform}"}
    return fn(entry, text)


# ───────────────────── platform impls ───────────────────────
def _stage(platform: str, text: str, ext: str = "md") -> Path:
    STAGE.mkdir(parents=True, exist_ok=True)
    f = STAGE / f"{platform}-{time.strftime('%Y%m%d-%H%M%S')}.{ext}"
    f.write_text(text, encoding="utf-8")
    return f


def _exec_wechat(entry: dict, text: str) -> dict:
    ctx = entry.get("context", {})
    title = ctx.get("topic", "")[:60] or "untitled"
    try:
        import wechat_draft
        r = wechat_draft.add_draft(title, text, cover_image=ctx.get("image"))
    except Exception as e:  # noqa: BLE001
        r = {"ok": False, "error": f"{type(e).__name__}: {e}"}
    if r.get("ok"):
        return {"ok": True,
                "detail": f"公众号草稿箱已推送 (media_id {r.get('media_id')})\n"
                          f"去微信公众平台后台「草稿箱」验证排版后发布"}
    f = _stage("wechat", text)
    return {"ok": True,
            "detail": f"公众号 API 推送失败: {r.get('error')}\n已暂存 → {f}"}


def _exec_x(entry: dict, text: str) -> dict:
    f = _stage("x", text, ext="txt")
    return {"ok": True, "detail": f"X 草稿已暂存 → {f}\n手动 Cmd+V 发布 (X API 后续接)"}


def _exec_linkedin(entry: dict, text: str) -> dict:
    env_file = HOME / ".secrets" / "linkedin.env"
    if not env_file.exists():
        f = _stage("linkedin", text, ext="txt")
        return {"ok": True,
                "detail": f"LinkedIn 暂存 → {f}\n(OAuth 未配; 跑 li-oauth.py 后可自动发)"}
    env = dict(os.environ)
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    cmd = ["python3", str(SELF_MEDIA / "tools" / "linkedin" / "li-post.py"), text]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "li-post.py timed out"}
    if out.returncode != 0:
        return {"ok": False, "error": out.stderr.strip()[:300] or "li-post failed"}
    url = next((ln.strip() for ln in out.stdout.splitlines()
                if "linkedin.com/feed" in ln), "")
    return {"ok": True, "detail": "posted to LinkedIn", "url": url}


def _exec_xhs(entry: dict, text: str) -> dict:
    ctx = entry["context"]
    title = ctx.get("topic", "")[:20] or "untitled"
    tags = "AI,ClaudeCode,生产力,AI工具"
    cmd = ["npx", "xhs-mcp", "publish", "--type", "image",
           "--title", title, "--content", text, "--tags", tags]
    img = ctx.get("image")
    if not img:
        try:
            import image_gen
            covers = SELF_MEDIA / "content" / "_covers"
            out = covers / f"xhs-{time.strftime('%Y%m%d-%H%M%S')}.png"
            img = str(image_gen.generate_image(
                image_gen.cover_prompt(ctx.get("topic", ""), "xiaohongshu"),
                out, size="1024x1536"))
        except Exception:  # noqa: BLE001
            img = None
    if img:
        cmd += ["--media", img]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "xhs-mcp timed out"}
    if out.returncode != 0:
        return {"ok": False, "error": out.stderr.strip()[:300] or "xhs-mcp failed"}
    try:
        data = json.loads(out.stdout.strip().splitlines()[-1])
        return {"ok": bool(data.get("success")), "detail": data.get("title", ""),
                "url": data.get("url", "")}
    except Exception:  # noqa: BLE001
        return {"ok": True, "detail": "published (xhs-mcp output unparsed)"}


def _exec_video(entry: dict, text: str) -> dict:
    """抖音/TikTok — stage the script + spec for autopost.video.

    Video generation is expensive (1-7 min, API cost). This stages the
    approved script; actual mp4 generation is triggered separately so the
    rendered video itself gets a second Telegram preview-card approval.
    """
    platform = entry["context"]["platform"]
    spec = {
        "platform": platform,
        "topic": entry["context"].get("topic", ""),
        "script": text,
        "playbook_variant": entry["context"].get("playbook_variant", ""),
        "staged_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "next": "render via ~/autopost.video, then preview-card approve",
    }
    f = _stage(platform, json.dumps(spec, ensure_ascii=False, indent=2), ext="json")
    return {"ok": True,
            "detail": f"{platform} 脚本已暂存 → {f}\n"
                      f"下一步: autopost.video 生成 mp4 → Telegram 预览卡二次审核"}


# ───────────────────────── helpers ──────────────────────────
def _read(path: Path, limit: int = 4000) -> str:
    return path.read_text(encoding="utf-8")[:limit] if path.exists() else ""


def _llm(prompt: str) -> str:
    try:
        from openai import OpenAI
    except ImportError:
        return "[LLM unavailable — pip install openai]"
    base = os.environ.get("LLM_BASE_URL", "https://flatkey.ai/v1")
    key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
    model = os.environ.get("LLM_MODEL", "gpt-5-mini")
    if not key:
        return "[LLM unavailable — set LLM_API_KEY in .env]"
    client = OpenAI(base_url=base, api_key=key)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
    )
    return resp.choices[0].message.content or ""

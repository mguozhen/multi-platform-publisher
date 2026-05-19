"""Claude API 调用 — 走 `claude -p`，复用 Claude Code 订阅。

为什么不走 SDK / flatkey：
  - Hunter 没单独的 ANTHROPIC_API_KEY；flatkey 不路由 Claude 模型。
  - `claude -p` 跟用户登录态走（同 gtm-swarm 已验证的模式）。
  - 模型可选：默认 sonnet（平台改写够用），关键润色用 opus。
"""
from __future__ import annotations

import subprocess
from typing import Optional


CLAUDE_BIN = "/Users/hunter/.local/bin/claude"


def claude_adapt(
    article: str,
    playbook: str,
    platform: str,
    model: str = "sonnet",
    timeout: int = 300,
) -> str:
    """让 Claude 把 article 按 playbook 改写成 platform 原生版。

    返回平台原生文本（已剥 markdown 噪声、套好该平台格式）。失败抛 RuntimeError。
    """
    prompt = _build_prompt(article=article, playbook=playbook, platform=platform)
    try:
        proc = subprocess.run(
            [CLAUDE_BIN, "-p", prompt, "--model", model,
             "--output-format", "text", "--no-session-persistence"],
            capture_output=True, text=True, timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"claude 超时（{timeout}s）") from e
    if proc.returncode != 0:
        raise RuntimeError(f"claude exit {proc.returncode}: {proc.stderr[:400]}")
    out = (proc.stdout or "").strip()
    if not out:
        raise RuntimeError(f"claude 空输出：stderr={proc.stderr[:300]!r}")
    return out


def _build_prompt(*, article: str, playbook: str, platform: str) -> str:
    return f"""You adapt one article into a single platform-native post, strictly following the playbook below.

PLATFORM: {platform}

PLAYBOOK (the only style/format authority — obey it):
<<<PLAYBOOK
{playbook}
PLAYBOOK>>>

SOURCE ARTICLE (raw material, do not just copy):
<<<ARTICLE
{article}
ARTICLE>>>

OUTPUT RULES:
- Return ONLY the final post text, ready to paste. No preface, no explanation, no markdown fences.
- Obey the playbook's variant selection, length, hook, structure, formatting, and forbidden words.
- For platforms with a "no link in body" rule (LinkedIn), keep the body link-free.
- Reshape — don't translate or copy. Tone, length, format must be platform-native.
- No emoji unless the playbook explicitly endorses them for this platform.
- If the playbook offers multiple variants, pick the most appropriate ONE and write fully in it.
"""

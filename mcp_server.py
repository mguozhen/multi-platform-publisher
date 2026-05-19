"""multi-platform-publisher — MCP server.

Exposes the CLI's publish / preview / inspection commands as MCP tools so an
Agent can call them through stdio MCP, without spawning subprocesses or
guessing CLI flags.

Run as:
    python -m mcp_server          # stdio MCP server

Or register with Claude Code:
    claude mcp add mpp -- python -m mcp_server

Tools
-----
    adapt_content              — preview how content is reshaped per platform
    publish_to_platforms        — publish (or --dry-run) to N platforms in one call
    list_supported_platforms    — platform metadata: auth, limits, features
    validate_credentials        — check creds are present for a platform
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

# Make the repo importable when launched as `python -m mcp_server` from any cwd.
_REPO = Path(__file__).resolve().parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from mcp.server.fastmcp import FastMCP  # type: ignore

from adapters.twitter_adapter import TwitterAdapter
from adapters.linkedin_adapter import LinkedInAdapter
from adapters.wechat_adapter import WeChatAdapter
from adapters.xiaohongshu_adapter import XiaohongshuAdapter
from utils.config_loader import ConfigLoader
from utils.content_adapter import ContentAdapter


mcp = FastMCP("multi-platform-publisher")

_DOCS_ERRORS = "https://github.com/mguozhen/multi-platform-publisher/blob/main/docs/errors.md"

_PLATFORM_REGISTRY: dict[str, type] = {
    "twitter": TwitterAdapter,
    "linkedin": LinkedInAdapter,
    "wechat": WeChatAdapter,
    "xiaohongshu": XiaohongshuAdapter,
}
_PLATFORM_ALIASES: dict[str, str] = {"x": "twitter", "xhs": "xiaohongshu"}


def _err(type_: str, message: str, suggested_action: str, retryable: bool = False) -> dict:
    """Semantic error body — every tool returns errors in this shape."""
    return {
        "error": {
            "type": type_,
            "message": message,
            "suggested_action": suggested_action,
            "retryable": retryable,
            "docs_url": f"{_DOCS_ERRORS}#{type_}",
        }
    }


def _resolve_platform(name: str) -> str:
    n = (name or "").strip().lower()
    return _PLATFORM_ALIASES.get(n, n)


def _load_content(content: str | None, file_path: str | None) -> str | None:
    if content:
        return content
    if file_path:
        p = Path(file_path).expanduser()
        if not p.exists():
            return None
        return p.read_text(encoding="utf-8")
    return None


@mcp.tool()
def list_supported_platforms() -> dict[str, Any]:
    """List every platform this publisher can target via the MCP / CLI surface.

    Returns a list of platform descriptors with display name, auth method,
    feature flags, and content limits — what an Agent needs to pick the
    right target. Cheapest call (no network); use to pre-flight before
    publishing.

    Returns:
        {"platforms": [{id, display_name, auth_method, features, max_text_length, max_images, aliases}],
         "_meta": {"count": int, "aliases": {alias: canonical}}}
    """
    out = []
    for pid, cls in _PLATFORM_REGISTRY.items():
        out.append({
            "id": pid,
            "display_name": getattr(cls, "DISPLAY_NAME", pid.title()),
            "auth_method": getattr(cls, "AUTH_METHOD", "Unknown"),
            "features": list(getattr(cls, "FEATURES", []) or []),
            "max_text_length": getattr(cls, "MAX_TEXT_LENGTH", 0),
            "max_images": getattr(cls, "MAX_IMAGES", 0),
            "aliases": [a for a, c in _PLATFORM_ALIASES.items() if c == pid],
        })
    return {
        "platforms": out,
        "_meta": {"count": len(out), "aliases": _PLATFORM_ALIASES,
                  "docs_url": "https://github.com/mguozhen/multi-platform-publisher"},
    }


@mcp.tool()
def adapt_content(content: str | None = None, file_path: str | None = None,
                  platform: str | None = None, as_thread: bool = False) -> dict[str, Any]:
    """Preview how the content will be reshaped per platform — no posting.

    Use this BEFORE publishing to see exactly what each platform will receive:
    Twitter threads with numbering, LinkedIn paragraphs, WeChat HTML, XHS
    emoji + tags. Free — no network call.

    Args:
        content: inline text (markdown or plain). One of `content` / `file_path` required.
        file_path: path to a .md / .txt file (alternative to `content`).
        platform: target platform id (twitter/x, linkedin, wechat, xiaohongshu/xhs).
                  If omitted, returns adaptation for ALL 4 platforms.
        as_thread: hint for Twitter — split into a thread vs single tweet.

    Returns:
        {"adapted": {platform: <content>}, "_meta": {"source_chars": int}}
    """
    src = _load_content(content, file_path)
    if src is None:
        return _err("invalid_input",
                    "Provide either `content` (inline text) or `file_path` (path to a .md/.txt).",
                    "Pass one of `content` or `file_path` and retry.")

    adapter = ContentAdapter()
    if platform:
        canon = _resolve_platform(platform)
        if canon not in _PLATFORM_REGISTRY:
            return _err("unknown_platform",
                        f"Unknown platform {platform!r}.",
                        "Call list_supported_platforms() for the set of valid ids and aliases.")
        return {
            "adapted": {canon: adapter.adapt(src, canon, as_thread=as_thread)},
            "_meta": {"source_chars": len(src), "platform": canon, "as_thread": as_thread,
                      "docs_url": "https://github.com/mguozhen/multi-platform-publisher#content-adaptation"},
        }

    out = {pid: adapter.adapt(src, pid, as_thread=as_thread) for pid in _PLATFORM_REGISTRY}
    return {
        "adapted": out,
        "_meta": {"source_chars": len(src), "platforms": list(out), "as_thread": as_thread,
                  "docs_url": "https://github.com/mguozhen/multi-platform-publisher#content-adaptation"},
    }


@mcp.tool()
def validate_credentials(platform: str) -> dict[str, Any]:
    """Check whether the credentials for `platform` are present.

    Reads from env vars > `~/.openclaw/openclaw.json` > `config.json` (same
    precedence as the CLI). Does not make a network call — only checks key
    presence. Cheapest pre-flight before `publish_to_platforms`.

    Args:
        platform: target platform id (twitter/x, linkedin, wechat, xiaohongshu/xhs).

    Returns:
        {"platform": str, "ready": bool, "missing": [env_var, ...]} or a
        semantic error.
    """
    canon = _resolve_platform(platform)
    if canon not in _PLATFORM_REGISTRY:
        return _err("unknown_platform",
                    f"Unknown platform {platform!r}.",
                    "Call list_supported_platforms() for valid ids.")
    cfg = ConfigLoader().get_platform_config(canon)
    try:
        adapter = _PLATFORM_REGISTRY[canon](cfg)
        ok = bool(adapter.validate()) if hasattr(adapter, "validate") else True
    except Exception as exc:
        return _err("auth_missing",
                    f"Could not instantiate {canon} adapter: {exc}",
                    f"Set the required env vars for {canon} — see config.json.example or list_supported_platforms.")
    return {"platform": canon, "ready": bool(ok),
            "_meta": {"docs_url": "https://github.com/mguozhen/multi-platform-publisher#configuration"}}


@mcp.tool()
def publish_to_platforms(content: str | None = None, file_path: str | None = None,
                         platforms: list[str] | None = None,
                         images: list[str] | None = None,
                         as_thread: bool = False,
                         dry_run: bool = False) -> dict[str, Any]:
    """Publish a piece of content to one or more platforms in one call.

    `platforms=None` or `["all"]` fans out to all 4. Per-platform errors are
    isolated — a Twitter failure won't stop the LinkedIn post. Use `dry_run`
    (or call `adapt_content`) to preview without posting. Cost depends on
    platform APIs.

    Args:
        content: inline text (markdown or plain). One of `content` / `file_path` required.
        file_path: path to a .md / .txt file (alternative to `content`).
        platforms: list of platform ids (twitter/x, linkedin, wechat, xiaohongshu/xhs).
                   None or ["all"] = every supported platform.
        images: optional list of image file paths to attach.
        as_thread: Twitter hint — split into a thread vs single tweet.
        dry_run: True = adapt and return the would-be payload, NEVER post.

    Returns:
        {"results": {platform: {"ok": bool, "url"?: str, "draft_id"?: str, "error"?: ...}},
         "_meta": {"dry_run": bool, "summary": "X/Y published"}}
    """
    src = _load_content(content, file_path)
    if src is None:
        return _err("invalid_input",
                    "Provide either `content` or `file_path`.",
                    "Pass one of `content` or `file_path` and retry.")

    if not platforms or (len(platforms) == 1 and platforms[0].lower() == "all"):
        targets = list(_PLATFORM_REGISTRY.keys())
    else:
        targets = []
        for p in platforms:
            canon = _resolve_platform(p)
            if canon not in _PLATFORM_REGISTRY:
                return _err("unknown_platform",
                            f"Unknown platform {p!r}.",
                            "Call list_supported_platforms() for valid ids.")
            targets.append(canon)

    adapter_engine = ContentAdapter()
    results: dict[str, Any] = {}
    cfg_loader = ConfigLoader()

    for pid in targets:
        adapted = adapter_engine.adapt(src, pid, as_thread=as_thread)
        if dry_run:
            results[pid] = {"ok": True, "dry_run": True, "preview": adapted}
            continue
        try:
            adapter = _PLATFORM_REGISTRY[pid](cfg_loader.get_platform_config(pid))
            if hasattr(adapter, "validate") and not adapter.validate():
                results[pid] = _err("auth_missing",
                                    f"{pid} credentials not configured.",
                                    f"Set the required env vars for {pid} — see config.json.example.")["error"]
                results[pid] = {"ok": False, **{"error": results[pid]}}
                continue
            res = adapter.publish(adapted, images=images)
            results[pid] = {"ok": True, **(res if isinstance(res, dict) else {"result": res})}
        except Exception as exc:
            results[pid] = {"ok": False, "error": _err("publish_failed",
                                                       f"{pid} publish raised: {exc}",
                                                       "Retry once; if it persists, check credentials and that the platform API is reachable.",
                                                       retryable=True)["error"]}

    ok_count = sum(1 for r in results.values() if r.get("ok"))
    return {
        "results": results,
        "_meta": {
            "dry_run": dry_run,
            "summary": f"{ok_count}/{len(targets)} {'previewed' if dry_run else 'published'}",
            "platforms": targets,
            "docs_url": "https://github.com/mguozhen/multi-platform-publisher#quick-start",
        },
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()

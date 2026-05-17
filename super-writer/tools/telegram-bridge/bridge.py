#!/usr/bin/env python3
"""
Telegram bridge — 内容抽卡 + human-in-the-loop approval.

Two card kinds flow through one Telegram long-poll loop:

  TOPIC BATCH  — 3 选题卡。你点 ✍️ 选一张 → 选平台 → 选 playbook
                 → 生成草稿 → 转成 DRAFT CARD
  DRAFT CARD   — 草稿卡。✅ Approve / 🔄 Regen / ❌ Reject
                 reject → 问原因 → 自动 regen 把原因作负例

USAGE
  python3 bridge.py --run                       run the long-poll loop
  python3 bridge.py --discover-chat             print chat_id
  python3 bridge.py --enqueue --draft "..." --context '{}'   push a draft card
  python3 bridge.py --enqueue-cards '<json>'    push a topic batch (gacha calls this)

ENV (.env, auto-loaded)
  TELEGRAM_BOT_TOKEN  TELEGRAM_CHAT_ID  BRIDGE_HOOKS
  LLM_API_KEY  LLM_BASE_URL  LLM_MODEL
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import secrets
import subprocess
import sys
import time
from pathlib import Path

import telegram

HERE = Path(__file__).resolve().parent
SELF_MEDIA = HERE.parent.parent          # ~/self-media
QUEUE_FILE = HERE / "queue.json"
STATE_FILE = HERE / ".bridge_state.json"
DISCOVERED_FILE = HERE / "discovered_chats.json"
PLAYBOOKS = SELF_MEDIA / "playbooks"
FEEDBACK_LOG = SELF_MEDIA / "inbox" / "telegram_feedback.jsonl"
MEDIA_DIR = SELF_MEDIA / "inbox" / "media"

PLATFORMS = {
    "wechat": "公众号", "x": "X", "linkedin": "LinkedIn",
    "xiaohongshu": "小红书", "douyin": "抖音", "tiktok": "TikTok",
}


# ───────────────────────── env ─────────────────────────
def load_env() -> None:
    env_file = HERE / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def token() -> str:
    t = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not t:
        sys.exit("ERROR: TELEGRAM_BOT_TOKEN not set (see .env)")
    return t


def chat_id() -> str:
    c = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not c:
        sys.exit("ERROR: TELEGRAM_CHAT_ID not set — run --discover-chat first")
    return c


def group_chat_id() -> str:
    """可选的群 chat_id (TELEGRAM_GROUP_CHAT_ID)。"""
    return os.environ.get("TELEGRAM_GROUP_CHAT_ID", "").strip()


def push_chat() -> str:
    """抽卡 / 草稿默认推送目标 — 配了群就发群，否则私聊。"""
    return group_chat_id() or str(chat_id())


def authorized_chats() -> set:
    """允许操作 bot 的 chat 集合 — 私聊 + 群 (如配)。"""
    chats = {str(chat_id())}
    g = group_chat_id()
    if g:
        chats.add(g)
    return chats


def record_unknown_chat(chat: dict) -> None:
    """把陌生 chat 写进 discovered_chats.json，方便发现群 chat_id。"""
    data = {}
    if DISCOVERED_FILE.exists():
        try:
            data = json.loads(DISCOVERED_FILE.read_text() or "{}")
        except json.JSONDecodeError:
            data = {}
    data[str(chat.get("id"))] = {
        "type": chat.get("type"),
        "title": (chat.get("title") or chat.get("username")
                  or chat.get("first_name") or "?"),
        "seen_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    DISCOVERED_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))


# ─────────────────── feedback inbox ─────────────────────
def record_feedback(from_chat: str, text: str,
                     reply_ctx: str | None = None) -> int:
    """自由文本指令 / review → 落到 inbox 供 Claude 下次读取。返回未读条数。"""
    FEEDBACK_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "chat_id": from_chat,
        "text": text,
        "reply_ctx": reply_ctx,
        "status": "unread",
    }
    with FEEDBACK_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return sum(1 for ln in FEEDBACK_LOG.read_text(encoding="utf-8").splitlines()
               if ln.strip() and '"status": "unread"' in ln)


# ─────────────────────── queue I/O ──────────────────────
def load_queue() -> list[dict]:
    if QUEUE_FILE.exists():
        return json.loads(QUEUE_FILE.read_text() or "[]")
    return []


def save_queue(q: list[dict]) -> None:
    QUEUE_FILE.write_text(json.dumps(q, ensure_ascii=False, indent=2))


def find(q: list[dict], entry_id: str) -> dict | None:
    return next((e for e in q if e["id"] == entry_id), None)


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text() or "{}")
    return {}


def save_state(s: dict) -> None:
    STATE_FILE.write_text(json.dumps(s, ensure_ascii=False, indent=2))


# ─────────────────────── hooks ──────────────────────────
def get_hooks():
    mod_name = os.environ.get("BRIDGE_HOOKS", "hooks_demo")
    sys.path.insert(0, str(HERE))
    mod = importlib.import_module(mod_name)
    if not hasattr(mod, "generate") or not hasattr(mod, "execute"):
        sys.exit(f"ERROR: hooks module '{mod_name}' must define generate() and execute()")
    return mod


# ─────────────────── playbook variants ──────────────────
def playbook_variants(platform: str) -> list[str]:
    """Parse '### variant X — ...' headers from playbooks/<platform>.md."""
    f = PLAYBOOKS / f"{platform}.md"
    if not f.exists():
        return ["A"]
    variants = []
    for ln in f.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if ln.startswith("### variant "):
            # "### variant A — build 推文" → label "A — build 推文"
            variants.append(ln[len("### variant "):].strip())
    return variants or ["A"]


# ═══════════════════ DRAFT CARD flow ════════════════════
def enqueue(draft_text: str, context: dict, label: str = "") -> dict:
    q = load_queue()
    target = push_chat()
    entry = {
        "id": secrets.token_hex(3),
        "kind": "draft",
        "label": label,
        "draft_text": draft_text,
        "context": context,
        "status": "pending",
        "chat_id": target,
        "telegram_message_id": None,
        "rejection_reasons": [],
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "result": None,
    }
    mid = telegram.send_card(token(), target, entry)
    entry["telegram_message_id"] = mid
    q.append(entry)
    save_queue(q)
    print(f"enqueued draft {entry['id']} → telegram message {mid}")
    return entry


def handle_approve(entry: dict, hooks) -> None:
    cid = entry.get("chat_id") or chat_id()
    entry["status"] = "executing"
    entry["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    telegram.edit_card(token(), cid, entry, footer="⏳ executing…", buttons=False)
    try:
        result = hooks.execute(entry)
    except Exception as e:  # noqa: BLE001
        result = {"ok": False, "error": f"{type(e).__name__}: {e}"}
    entry["result"] = result
    if result.get("ok"):
        entry["status"] = "executed"
        footer = "✅ APPROVED & EXECUTED"
        if result.get("url"):
            footer += f"\n{result['url']}"
        elif result.get("detail"):
            footer += f"\n{result['detail']}"
    else:
        entry["status"] = "failed"
        footer = f"⚠️ EXECUTE FAILED\n{result.get('error', 'unknown')}"
    telegram.edit_card(token(), cid, entry, footer=footer, buttons=False)


def handle_regen(entry: dict, hooks, reason: str | None = None) -> None:
    cid = entry.get("chat_id") or chat_id()
    entry["status"] = "regenerating"
    entry["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    if reason:
        entry["rejection_reasons"].append(reason)
    telegram.edit_card(token(), cid, entry, footer="🔄 regenerating…", buttons=False)
    try:
        new_draft = hooks.generate(entry)
    except Exception as e:  # noqa: BLE001
        entry["status"] = "failed"
        telegram.edit_card(token(), cid, entry,
                           footer=f"⚠️ REGEN FAILED\n{type(e).__name__}: {e}",
                           buttons=False)
        return
    entry["draft_text"] = new_draft
    entry["status"] = "pending"
    mid = telegram.send_card(token(), cid, entry)
    entry["telegram_message_id"] = mid


def handle_reject(entry: dict) -> None:
    cid = entry.get("chat_id") or chat_id()
    entry["status"] = "awaiting_reason"
    entry["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    telegram.edit_card(token(), cid, entry,
                       footer="❌ rejected — reply with the reason 👇", buttons=False)


# ═══════════════════ TOPIC BATCH flow ═══════════════════
def _card_batch_text(batch: dict) -> str:
    lines = ["🎴 *今日抽卡* — 选一张来写\n"]
    comments = batch.get("comments") or []
    if comments:
        lines.append("*Comments / 优化意见*")
        for c in comments[-3:]:
            lines.append(f"• {c}")
        lines.append("")
    for i, c in enumerate(batch["cards"], 1):
        plats = "/".join(c.get("suggested_platforms", []))
        lines.append(f"*卡{i}* `[{c['source']}·{c['score']}]`")
        lines.append(f"{c['title']}")
        lines.append(f"_建议: {plats}_\n")
    return "\n".join(lines)


def _card_batch_buttons(batch: dict) -> list:
    bid = batch["id"]
    n = len(batch["cards"])
    pick_row = [(f"✍️ 写卡{i+1}", f"pk:{bid}:{i}") for i in range(n)]
    return [pick_row, [("💬 Comments", f"cm:{bid}"), ("🔄 换一批", f"rb:{bid}")]]


def enqueue_cards(cards: list[dict]) -> dict:
    """Push a topic batch (called by gacha.py --push)."""
    q = load_queue()
    target = push_chat()
    batch = {
        "id": secrets.token_hex(3),
        "kind": "topic_batch",
        "cards": cards,
        "status": "pending",
        "chat_id": target,
        "telegram_message_id": None,
        "picked_idx": None,
        "platform": None,
        "comments": [],
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    mid = telegram.send_buttons(token(), target,
                                _card_batch_text(batch), _card_batch_buttons(batch))
    batch["telegram_message_id"] = mid
    q.append(batch)
    save_queue(q)
    print(f"enqueued topic batch {batch['id']} → telegram message {mid}")
    return batch


def handle_pick(batch: dict, idx: int) -> None:
    """User picked a card → ask which platform."""
    batch["picked_idx"] = idx
    batch["status"] = "picked"
    card = batch["cards"][idx]
    bid = batch["id"]
    text = f"🎴 已选: *{card['title']}*\n\n发哪个平台?"
    rows = [
        [(PLATFORMS["wechat"], f"pf:{bid}:wechat"),
         (PLATFORMS["x"], f"pf:{bid}:x"),
         (PLATFORMS["linkedin"], f"pf:{bid}:linkedin")],
        [(PLATFORMS["xiaohongshu"], f"pf:{bid}:xiaohongshu"),
         (PLATFORMS["douyin"], f"pf:{bid}:douyin"),
         (PLATFORMS["tiktok"], f"pf:{bid}:tiktok")],
        [("🌐 全平台 — 全部生成 + 公网预览", f"pf:{bid}:all")],
    ]
    cid = batch.get("chat_id") or chat_id()
    telegram.edit_buttons(token(), cid, batch["telegram_message_id"], text, rows)


def handle_batch_comments(batch: dict) -> None:
    """Ask the user to reply with comments that refine this draw batch."""
    batch["status"] = "awaiting_comments"
    cid = batch.get("chat_id") or chat_id()
    text = (
        f"💬 给这批抽卡加 comments\n\n"
        f"直接回复优化意见。我会保存到这批卡里，并带进后续出稿。\n\n"
        f"可选格式:\n"
        f"卡2：把重点改成 1 星差评找新品\n"
        f"整体：更像抖音爆款，标题更狠"
    )
    telegram.edit_buttons(token(), cid, batch["telegram_message_id"], text, None)


def _apply_comment_title_edits(batch: dict, comment: str) -> None:
    """Support quick manual edits: `卡2：new title` updates card 2 title."""
    for m in re.finditer(r"卡\s*([1-9]\d*)\s*[：:]\s*([^\n]+)", comment):
        idx = int(m.group(1)) - 1
        title = m.group(2).strip()
        if 0 <= idx < len(batch.get("cards", [])) and title:
            batch["cards"][idx]["title"] = title


def handle_batch_comment_reply(batch: dict, comment: str) -> None:
    """Persist comments and redraw the card batch in place."""
    batch.setdefault("comments", []).append(comment)
    _apply_comment_title_edits(batch, comment)
    batch["status"] = "pending"
    batch["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    cid = batch.get("chat_id") or chat_id()
    telegram.edit_buttons(
        token(), cid, batch["telegram_message_id"],
        _card_batch_text(batch), _card_batch_buttons(batch),
    )


def handle_platform(batch: dict, platform: str, hooks, q: list) -> None:
    """User picked platform → ask which playbook variant (or run 全平台)."""
    batch["platform"] = platform
    if platform == "all":
        handle_all_platforms(batch, hooks, q)
        return
    batch["status"] = "platform_chosen"
    card = batch["cards"][batch["picked_idx"]]
    bid = batch["id"]
    variants = playbook_variants(platform)
    text = (f"🎴 *{card['title']}*\n平台: {PLATFORMS.get(platform, platform)}\n\n"
            f"用哪个 playbook?")
    # button label = full variant description (Telegram caps ~ leave room)
    rows = [[(v[:48], f"pb:{bid}:{i}")] for i, v in enumerate(variants)]
    cid = batch.get("chat_id") or chat_id()
    telegram.edit_buttons(token(), cid, batch["telegram_message_id"], text, rows)


def handle_playbook(batch: dict, variant_idx: int, hooks, q: list) -> None:
    """User picked playbook variant → generate draft → spawn a draft card.

    The draft is appended to the caller's `q`; the dispatcher owns save_queue.
    """
    batch["status"] = "writing"
    card = batch["cards"][batch["picked_idx"]]
    platform = batch["platform"]
    cid = batch.get("chat_id") or chat_id()
    variants = playbook_variants(platform)
    variant = variants[variant_idx] if variant_idx < len(variants) else variants[0]

    telegram.edit_buttons(token(), cid, batch["telegram_message_id"],
                          f"🎴 *{card['title']}*\n平台: {PLATFORMS.get(platform)}\n"
                          f"playbook: {variant}\n\n⏳ 生成草稿中…", None)

    draft = _make_draft(card, platform, variant, cid, batch.get("comments", []))
    try:
        draft["draft_text"] = hooks.generate(draft)
    except Exception as e:  # noqa: BLE001
        telegram.send_message(token(), cid,
                              f"⚠️ 生成失败: {type(e).__name__}: {e}")
        batch["status"] = "failed"
        return
    mid = telegram.send_card(token(), cid, draft)
    draft["telegram_message_id"] = mid
    q.append(draft)
    batch["status"] = "done"


def _make_draft(card: dict, platform: str, variant: str, chat: str,
                draw_comments: list[str] | None = None) -> dict:
    """Build a draft entry skeleton (used by 全平台 + single-platform flows)."""
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    return {
        "id": secrets.token_hex(3),
        "kind": "draft",
        "label": f"{PLATFORMS.get(platform, platform)} · {card['source']}",
        "draft_text": "",
        "context": {
            "platform": platform,
            "topic": card["title"],
            "rationale": card.get("rationale", ""),
            "draw_comments": "\n".join(draw_comments or []),
            "playbook_variant": variant,
            "source_ref": card.get("source_ref", ""),
            "full_content": card.get("_full_content", ""),
        },
        "status": "pending",
        "chat_id": chat,
        "telegram_message_id": None,
        "rejection_reasons": [],
        "created_at": now,
        "updated_at": now,
        "result": None,
    }


def handle_all_platforms(batch: dict, hooks, q: list) -> None:
    """全平台: 生成 6 平台内容 → 公众号推草稿箱 + 其余 5 平台出公网预览 → 逐平台审核卡。

    新增的草稿卡 append 进调用方传入的 `q`；save_queue 由 dispatcher 统一负责。
    """
    batch["status"] = "writing"
    card = batch["cards"][batch["picked_idx"]]
    tok = token()
    cid = batch.get("chat_id") or chat_id()
    telegram.edit_buttons(tok, cid, batch["telegram_message_id"],
                          f"🎴 *{card['title']}*\n🌐 全平台生成中… (6 平台，约 1-2 分钟)",
                          None)

    # 1. generate every platform with its first playbook variant
    drafts: dict[str, dict] = {}
    for platform in PLATFORMS:
        variants = playbook_variants(platform)
        draft = _make_draft(
            card, platform, variants[0] if variants else "A", cid,
            batch.get("comments", []),
        )
        try:
            draft["draft_text"] = hooks.generate(draft)
        except Exception as e:  # noqa: BLE001
            draft["draft_text"] = f"[生成失败: {type(e).__name__}: {e}]"
        drafts[platform] = draft

    # 2. 公众号 → 真推草稿箱
    import wechat_draft
    wx = drafts["wechat"]
    try:
        wx_result = wechat_draft.add_draft(card["title"], wx["draft_text"])
    except Exception as e:  # noqa: BLE001
        wx_result = {"ok": False, "error": f"{type(e).__name__}: {e}"}
    wx["status"] = "executed" if wx_result.get("ok") else "failed"
    wx["result"] = wx_result

    # 3. 其余 5 平台 → 公网预览页 (Vercel)
    import allplatform_preview
    others = {p: drafts[p] for p in PLATFORMS if p != "wechat"}
    try:
        preview = allplatform_preview.build_and_deploy(card, others, wx_result)
    except Exception as e:  # noqa: BLE001
        preview = {"url": None, "error": f"{type(e).__name__}: {e}"}

    # 4. 汇报
    lines = [f"🌐 全平台生成完毕 — {card['title']}", ""]
    if wx_result.get("ok"):
        lines.append("✅ 公众号: 已推送到草稿箱，去微信公众平台后台验证排版")
    else:
        lines.append(f"⚠️ 公众号草稿失败: {wx_result.get('error')}")
    if preview.get("url"):
        lines.append(f"🔗 公网预览 (其余 5 平台): {preview['url']}")
    else:
        lines.append(f"⚠️ 预览部署失败: {preview.get('error')}")
        if preview.get("local_path"):
            lines.append(f"   本地 HTML: {preview['local_path']}")
    lines.append("")
    lines.append("👇 看完预览，逐平台 ✅Approve / 🔄Regen / ❌Reject")
    telegram.send_message(tok, cid, "\n".join(lines))

    # 5. 推 5 张逐平台审核卡 + 入队 (公众号已发，仅留记录)
    q.append(wx)
    for platform in ("x", "linkedin", "xiaohongshu", "douyin", "tiktok"):
        d = drafts[platform]
        mid = telegram.send_card(tok, cid, d)
        d["telegram_message_id"] = mid
        q.append(d)
    batch["status"] = "done"


def handle_imagegen(chat: str, prompt: str) -> None:
    """生图指令 — 调 image_gen (nano banana) 出图，发回该 chat。"""
    tok = token()
    if not prompt:
        telegram.send_message(tok, chat,
                              "用法: 生图 <描述>\n例: 生图 一只赛博朋克风格的猫")
        return
    telegram.send_message(tok, chat, f"🎨 生成中… {prompt[:40]}")
    try:
        import image_gen
        out = (SELF_MEDIA / "content" / "_covers"
               / f"img-{time.strftime('%Y%m%d-%H%M%S')}.png")
        image_gen.generate_image(prompt, out, size="1024x1024")
        telegram.send_photo(tok, chat, str(out), caption=f"🎨 {prompt[:200]}")
    except Exception as e:  # noqa: BLE001
        telegram.send_message(tok, chat,
                              f"⚠️ 生图失败: {type(e).__name__}: {e}")


def handle_media_upload(msg: dict, media_obj: dict, media_kind: str,
                        from_chat: str, q: list) -> None:
    """收到视频/图片/文件 → 下载到 inbox/media → 视频弹平台卡，图片存素材并记反馈。"""
    tok = token()
    file_id = media_obj.get("file_id")
    size = media_obj.get("file_size", 0) or 0
    caption = (msg.get("caption") or "").strip()
    dur = media_obj.get("duration")
    if size and size > 20 * 1024 * 1024:
        telegram.send_message(tok, from_chat,
            f"⚠️ 文件 {size/1048576:.1f}MB，超 Telegram Bot 下载上限 20MB。\n"
            f"压到 20MB 以内再发，或把本地路径直接 @我 发过来。")
        return
    label = "图片" if media_kind == "photo" else "视频"
    telegram.send_message(tok, from_chat, f"📥 下载{label}中…")
    try:
        path = telegram.download_file(tok, file_id, str(MEDIA_DIR))
    except Exception as e:  # noqa: BLE001
        telegram.send_message(tok, from_chat,
                              f"⚠️ 下载失败: {type(e).__name__}: {e}")
        return

    # ── 图片: 存素材 + 记反馈，不弹发布卡 (图片用途多义，等指令) ──
    if media_kind == "photo":
        n = record_feedback(from_chat, caption or "[发了一张图片]",
                            reply_ctx=f"image={path}")
        telegram.send_message(tok, from_chat,
            f"🖼 图片已存为素材: {path}\n"
            + (f"你的话: {caption}\n" if caption else "")
            + f"已记进 inbox (第 {n} 条未读)。\n"
            f"要拿它当某篇文章封面 / 发图文，@我说清楚是哪篇，"
            f"Claude 进来就办。")
        return

    # ── 视频: 弹平台发布卡 ──
    entry = {
        "id": secrets.token_hex(3),
        "kind": "media",
        "media_path": str(path),
        "caption": caption,
        "platform": None,
        "status": "pending",
        "chat_id": from_chat,
        "telegram_message_id": None,
        "result": {},
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    parts = [f"📹 收到视频 ({size/1048576:.1f}MB"
             + (f", {dur}s)" if dur else ")")]
    if caption:
        parts.append(f"caption: {caption[:160]}")
    parts.append("\n发哪个平台?")
    bid = entry["id"]
    rows = [
        [("X", f"mp:{bid}:x"), ("小红书", f"mp:{bid}:xiaohongshu"),
         ("抖音", f"mp:{bid}:douyin")],
        [("TikTok", f"mp:{bid}:tiktok"), ("YouTube", f"mp:{bid}:youtube"),
         ("视频号", f"mp:{bid}:shipinhao")],
    ]
    mid = telegram.send_buttons(tok, from_chat, "\n".join(parts), rows,
                                markdown=False)
    entry["telegram_message_id"] = mid
    q.append(entry)


def _publish_video_x(entry: dict, text: str) -> None:
    """上传 entry 的视频 + 发推到 X。就地更新卡。"""
    tok = token()
    cid = entry.get("chat_id") or chat_id()
    mid = entry["telegram_message_id"]
    if len(text) > 280:
        entry["status"] = "awaiting_caption"
        telegram.edit_buttons(tok, cid, mid,
            f"⚠️ 文案 {len(text)} 字，超 X 280 上限。\n"
            f"回复这条消息发更短的文案。", None, markdown=False)
        return
    entry["status"] = "publishing"
    telegram.edit_buttons(tok, cid, mid,
        "📹 → X 发布中…\n上传视频 + 转码（约 1-3 分钟，别急）", None,
        markdown=False)
    try:
        import x_post
        r = x_post.post_video(text, entry["media_path"])
        entry["status"] = "executed"
        entry["result"] = {"ok": True, **r}
        telegram.edit_buttons(tok, cid, mid,
            f"✅ X 视频已发布\n{r['url']}\n\n文案:\n{text}", None,
            markdown=False)
    except Exception as e:  # noqa: BLE001
        entry["status"] = "failed"
        entry["result"] = {"ok": False, "error": str(e)}
        telegram.edit_buttons(tok, cid, mid,
            f"⚠️ X 发布失败\n{type(e).__name__}: {e}\n\n"
            f"回复这条消息可重发文案。", None, markdown=False)


def handle_media_platform(entry: dict, platform: str, q: list) -> None:
    """媒体卡选了平台 → X 直接发；其余平台先占位。"""
    tok = token()
    cid = entry.get("chat_id") or chat_id()
    mid = entry["telegram_message_id"]
    entry["platform"] = platform
    if platform == "x":
        caption = (entry.get("caption") or "").strip()
        if caption:
            _publish_video_x(entry, caption)
        else:
            entry["status"] = "awaiting_caption"
            telegram.edit_buttons(tok, cid, mid,
                "📹 视频 → X\n\n回复这条消息，把 X 文案发给我（≤280 字）。",
                None, markdown=False)
    else:
        entry["status"] = "pending"
        names = {"xiaohongshu": "小红书", "douyin": "抖音",
                 "tiktok": "TikTok", "youtube": "YouTube",
                 "shipinhao": "视频号"}
        telegram.edit_buttons(tok, cid, mid,
            f"📹 视频 → {names.get(platform, platform)}\n\n"
            f"这个平台的视频自动发布还没接进 bridge——先把 X 闭环跑通验证。\n"
            f"视频已存: {entry['media_path']}", None, markdown=False)


def handle_rebatch(chat: str | None = None) -> None:
    """User wants a fresh batch → re-run gacha. (gacha --push 自己发到 push_chat)"""
    gacha = SELF_MEDIA / "tools" / "gacha.py"
    cid = chat or push_chat()
    telegram.send_message(token(), cid, "🔄 重新抽卡中…")
    try:
        subprocess.run(["python3", str(gacha), "--draw", "--push"],
                       capture_output=True, text=True, timeout=120)
    except Exception as e:  # noqa: BLE001
        telegram.send_message(token(), cid, f"⚠️ 抽卡失败: {e}")


# ─────────────────────── main loop ──────────────────────
def run_loop() -> None:
    hooks = get_hooks()
    tok = token()
    allowed = authorized_chats()
    state = load_state()
    offset = state.get("offset")
    print(f"bridge running. authorized chats={sorted(allowed)}  "
          f"hooks={os.environ.get('BRIDGE_HOOKS','hooks_demo')}")
    print("Ctrl-C to stop.")

    while True:
        try:
            updates = telegram.get_updates(tok, offset=offset, timeout=25)
        except Exception as e:  # noqa: BLE001
            print(f"[poll error] {e}; retry in 5s")
            time.sleep(5)
            continue

        for upd in updates:
            offset = upd["update_id"] + 1

            # ---- inline button press ----
            cq = upd.get("callback_query")
            if cq:
                from_chat = str(cq.get("message", {}).get("chat", {}).get("id", ""))
                if from_chat not in allowed:
                    telegram.answer_callback(tok, cq["id"], "not authorized")
                    continue
                data = cq.get("data", "")
                print(f"[callback] chat={from_chat} data={data!r}", flush=True)
                telegram.answer_callback(tok, cq["id"])
                parts = data.split(":")
                action = parts[0]
                q = load_queue()

                _stale = ("⚠️ 这张卡已失效（不在当前队列，多半是早期遗留卡）。\n"
                          "重新「抽卡」或「生图」生成新卡即可。")
                # draft card actions
                if action in ("a", "g", "r") and len(parts) >= 2:
                    entry = find(q, parts[1])
                    if entry:
                        if action == "a":
                            handle_approve(entry, hooks)
                        elif action == "g":
                            handle_regen(entry, hooks)
                        elif action == "r":
                            handle_reject(entry)
                        save_queue(q)
                    else:
                        telegram.send_message(tok, from_chat, _stale)
                # topic batch actions
                elif action == "pk" and len(parts) == 3:
                    batch = find(q, parts[1])
                    if batch:
                        handle_pick(batch, int(parts[2]))
                        save_queue(q)
                    else:
                        telegram.send_message(tok, from_chat, _stale)
                elif action == "cm" and len(parts) == 2:
                    batch = find(q, parts[1])
                    if batch:
                        handle_batch_comments(batch)
                        save_queue(q)
                    else:
                        telegram.send_message(tok, from_chat, _stale)
                elif action == "pf" and len(parts) == 3:
                    batch = find(q, parts[1])
                    if batch:
                        handle_platform(batch, parts[2], hooks, q)
                        save_queue(q)
                    else:
                        telegram.send_message(tok, from_chat, _stale)
                elif action == "pb" and len(parts) == 3:
                    batch = find(q, parts[1])
                    if batch:
                        handle_playbook(batch, int(parts[2]), hooks, q)
                        save_queue(q)
                    else:
                        telegram.send_message(tok, from_chat, _stale)
                elif action == "mp" and len(parts) == 3:
                    entry = find(q, parts[1])
                    if entry:
                        handle_media_platform(entry, parts[2], q)
                        save_queue(q)
                    else:
                        telegram.send_message(tok, from_chat, _stale)
                elif action == "rb":
                    handle_rebatch(from_chat)
                continue

            # ---- plain text message ----
            msg = upd.get("message")
            if msg:
                chat = msg.get("chat", {})
                from_chat = str(chat.get("id", ""))
                raw = (msg.get("text") or msg.get("caption") or "").strip()
                # 去掉群里 @bot 前缀 / /cmd@bot 后缀
                text = re.sub(r"^@\S+\s*", "", raw)
                text = re.sub(r"@\w+$", "", text).strip()
                reply_to = msg.get("reply_to_message") or {}
                reply_mid = reply_to.get("message_id")
                print(f"[message] chat={from_chat} "
                      f"authorized={from_chat in allowed} text={text!r}",
                      flush=True)
                if from_chat not in allowed:
                    if text:
                        record_unknown_chat(chat)
                        telegram.send_message(tok, from_chat,
                            f"👋 这个对话的 chat_id 是 {from_chat}\n"
                            f"把它写进 bridge .env 的 TELEGRAM_GROUP_CHAT_ID，"
                            f"重启 bot 后就能在这里抽卡。")
                    continue
                # ---- 媒体上传: 视频 / 图片 / 文件 (永远处理，不看 @) ----
                media_obj, media_kind = None, None
                if msg.get("video") or msg.get("animation"):
                    media_obj = msg.get("video") or msg.get("animation")
                    media_kind = "video"
                elif msg.get("photo"):
                    media_obj = msg["photo"][-1]      # 最大尺寸
                    media_kind = "photo"
                elif msg.get("document"):
                    doc = msg["document"]
                    mime = str(doc.get("mime_type", ""))
                    if mime.startswith("video"):
                        media_obj, media_kind = doc, "video"
                    elif mime.startswith("image"):
                        media_obj, media_kind = doc, "photo"
                if media_obj:
                    q = load_queue()
                    handle_media_upload(msg, media_obj, media_kind,
                                        from_chat, q)
                    save_queue(q)
                    continue
                if not text:
                    continue
                q = load_queue()
                awaiting = next((e for e in q
                                 if e.get("kind") == "draft"
                                 and e["status"] == "awaiting_reason"
                                 and (e.get("chat_id") or from_chat) == from_chat),
                                None)
                awaiting_batch = next((e for e in q
                                       if e.get("kind") == "topic_batch"
                                       and e["status"] == "awaiting_comments"
                                       and (e.get("chat_id") or from_chat) == from_chat),
                                      None)
                if awaiting:
                    print(f"reject reason for {awaiting['id']}: {text}")
                    handle_regen(awaiting, hooks, reason=text)
                    save_queue(q)
                elif awaiting_batch:
                    print(f"batch comments for {awaiting_batch['id']}: {text}")
                    handle_batch_comment_reply(awaiting_batch, text)
                    save_queue(q)
                elif text in ("抽卡", "draw", "/draw"):
                    handle_rebatch(from_chat)
                elif text.startswith(("生图", "画图", "/img")):
                    p = re.sub(r"^(生图|画图|/img)\s*", "", text).strip()
                    handle_imagegen(from_chat, p)
                elif text.lower() in ("hi", "hello", "ping"):
                    telegram.send_message(tok, from_chat,
                                          "bridge alive ✅ — 发「抽卡」/「生图 …」/ 直接 @我留反馈")
                elif text in ("反馈", "feedback", "/feedback"):
                    unread = 0
                    if FEEDBACK_LOG.exists():
                        unread = sum(1 for ln in FEEDBACK_LOG.read_text(
                            encoding="utf-8").splitlines()
                            if '"status": "unread"' in ln)
                    telegram.send_message(tok, from_chat,
                        f"📥 inbox 里有 {unread} 条未读反馈，等 Claude 下次进来处理。")
                else:
                    # ① 回复某张卡 → 当作对那张卡的反馈，直接路由
                    target = None
                    if reply_mid:
                        target = next((e for e in q
                                       if e.get("telegram_message_id") == reply_mid),
                                      None)
                    if target and target.get("kind") == "media":
                        if target.get("status") in ("awaiting_caption",
                                                     "failed"):
                            if target.get("platform") == "x":
                                _publish_video_x(target, text)
                                save_queue(q)
                            else:
                                telegram.send_message(tok, from_chat,
                                    "这条视频卡还没选平台/平台不是 X，"
                                    "先点卡上的平台按钮。")
                        else:
                            telegram.send_message(tok, from_chat,
                                "这条视频卡已处理过。重发视频再来一遍。")
                    elif target and target.get("kind") == "draft":
                        telegram.send_message(tok, from_chat,
                            f"🔄 收到对「{target.get('label','草稿')}」的反馈，"
                            f"按你说的重做中…")
                        handle_regen(target, hooks, reason=text)
                        save_queue(q)
                    elif target and target.get("kind") == "topic_batch":
                        handle_batch_comment_reply(target, text)
                        save_queue(q)
                        telegram.send_message(tok, from_chat,
                                              "💬 已记进这批卡的 comments。")
                    # ② 其它自由文本 → 落 inbox + 回执 (绝不静默)
                    else:
                        ctx = None
                        if reply_to.get("text") or reply_to.get("caption"):
                            ctx = (reply_to.get("text")
                                   or reply_to.get("caption"))[:200]
                        n = record_feedback(from_chat, text, ctx)
                        telegram.send_message(tok, from_chat,
                            f"📥 收到「{text[:60]}」，已记进 inbox"
                            f"（第 {n} 条未读）。\n"
                            f"我是指令桥，不能即时跑自由指令——Claude 进来会读"
                            f" inbox 按你说的办。\n"
                            f"要即时出活:「抽卡」「生图 …」，发视频/图片，"
                            f"或【回复某张卡】让它重做。")

        state["offset"] = offset
        save_state(state)


# ───────────────────── discover chat ────────────────────
def discover_chat() -> None:
    tok = token()
    print("DM your bot 'hi' on Telegram, then this prints the chat_id…")
    updates = telegram.get_updates(tok, timeout=20)
    seen = {}
    for upd in updates:
        msg = upd.get("message") or upd.get("callback_query", {}).get("message")
        if msg:
            chat = msg.get("chat", {})
            seen[str(chat.get("id"))] = (chat.get("username") or chat.get("title")
                                         or chat.get("first_name", "?"))
    if not seen:
        print("No messages. DM the bot first, then re-run.")
        return
    print("\nFound chats:")
    for cid_, name in seen.items():
        print(f"  chat_id={cid_}   ({name})")


# ───────────────────────── cli ──────────────────────────
def main() -> None:
    load_env()
    ap = argparse.ArgumentParser(description="Telegram 抽卡 + approval bridge")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--discover-chat", action="store_true")
    ap.add_argument("--enqueue", action="store_true")
    ap.add_argument("--draft")
    ap.add_argument("--context", default="{}")
    ap.add_argument("--label", default="")
    ap.add_argument("--enqueue-cards", help="JSON array of topic cards (gacha calls this)")
    args = ap.parse_args()

    if args.discover_chat:
        discover_chat()
    elif args.enqueue_cards:
        try:
            cards = json.loads(args.enqueue_cards)
        except json.JSONDecodeError as e:
            sys.exit(f"--enqueue-cards bad JSON: {e}")
        enqueue_cards(cards)
    elif args.enqueue:
        if not args.draft:
            sys.exit("--enqueue needs --draft")
        try:
            ctx = json.loads(args.context)
        except json.JSONDecodeError as e:
            sys.exit(f"--context bad JSON: {e}")
        enqueue(args.draft, ctx, label=args.label)
    elif args.run:
        run_loop()
    else:
        ap.print_help()


if __name__ == "__main__":
    main()

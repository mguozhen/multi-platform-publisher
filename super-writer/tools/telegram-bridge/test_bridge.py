#!/usr/bin/env python3
"""
bridge.py 回归测试 — 不碰真 Telegram / 真 API，全程 mock。

覆盖:
  A  草稿卡 enqueue → approve → executed
  B  草稿卡 enqueue → regen → 新草稿
  C  草稿卡 reject → reason → regen 带负例
  D  抽卡 → pick → platform → playbook → 草稿持久化 + regen 找得到   ← regen bug 回归
  E  抽卡 → pick → 全平台 → 公众号记录 + 5 张草稿卡全部入队
  F  群路由 — 配 TELEGRAM_GROUP_CHAT_ID 后卡片 chat_id 指向群
  G  push_chat / authorized_chats 逻辑
  H  抽卡 comments → 改卡标题 + 带进草稿 context

跑: python3 test_bridge.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import bridge          # noqa: E402
import telegram        # noqa: E402

bridge.load_env()

PASS, FAIL = 0, 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {label}")
    else:
        FAIL += 1
        print(f"  ❌ {label}  {detail}")


# ───────────── mock telegram (记录调用，不发网络) ─────────────
SENT: list = []


def _reset_sent() -> None:
    SENT.clear()


telegram.send_card = lambda tok, chat, e: (
    SENT.append(("send_card", str(chat), e["id"])) or (9000 + len(SENT)))
telegram.edit_card = lambda tok, chat, e, footer=None, buttons=True: (
    SENT.append(("edit_card", str(chat), e["id"])))
telegram.send_buttons = lambda tok, chat, text, rows: (
    SENT.append(("send_buttons", str(chat), text[:20])) or (8000 + len(SENT)))
telegram.edit_buttons = lambda tok, chat, mid, text, rows=None: (
    SENT.append(("edit_buttons", str(chat), mid)))
telegram.send_message = lambda tok, chat, text: (
    SENT.append(("send_message", str(chat), text[:20])) or (7000 + len(SENT)))
telegram.answer_callback = lambda tok, qid, text="": None

# ───────────── fake hooks ─────────────
fake_hooks = types.SimpleNamespace(
    generate=lambda entry: f"[draft:{entry['context'].get('platform','?')}:"
                           f"{len(entry.get('rejection_reasons', []))}]",
    execute=lambda entry: {"ok": True, "detail": "mock executed"},
)

# ───────────── 隔离 queue / state ─────────────
TMP = Path(tempfile.mkdtemp(prefix="bridgetest-"))
bridge.QUEUE_FILE = TMP / "queue.json"
bridge.STATE_FILE = TMP / "state.json"
bridge.DISCOVERED_FILE = TMP / "discovered.json"


def fresh_queue() -> None:
    bridge.save_queue([])


def sample_cards() -> list:
    return [{
        "id": f"c{i}", "kind": "topic", "title": f"选题{i}",
        "source": "github", "score": 0.7, "rationale": "值得发",
        "suggested_platforms": ["x"], "_full_content": "",
    } for i in range(1, 4)]


# ═══════════════ A — 草稿 approve ═══════════════
def test_a() -> None:
    print("\n[A] 草稿卡 enqueue → approve")
    fresh_queue()
    _reset_sent()
    entry = bridge.enqueue("hello draft", {"platform": "x", "topic": "t"}, "X·test")
    q = bridge.load_queue()
    e = bridge.find(q, entry["id"])
    check("enqueue 后草稿在队列里", e is not None)
    bridge.handle_approve(e, fake_hooks)
    bridge.save_queue(q)
    e = bridge.find(bridge.load_queue(), entry["id"])
    check("approve 后 status=executed", e["status"] == "executed", str(e["status"]))
    check("approve 结果 ok", e["result"]["ok"])


# ═══════════════ B — 草稿 regen ═══════════════
def test_b() -> None:
    print("\n[B] 草稿卡 regen")
    fresh_queue()
    _reset_sent()
    entry = bridge.enqueue("v1", {"platform": "x", "topic": "t"})
    q = bridge.load_queue()
    e = bridge.find(q, entry["id"])
    old_text = e["draft_text"]
    bridge.handle_regen(e, fake_hooks)
    bridge.save_queue(q)
    e = bridge.find(bridge.load_queue(), entry["id"])
    check("regen 后 status 回到 pending", e["status"] == "pending", str(e["status"]))
    check("regen 后 draft_text 变了", e["draft_text"] != old_text)
    check("regen 发了新卡片", ("send_card", e["chat_id"], e["id"]) in SENT)


# ═══════════════ C — reject → reason → regen ═══════════════
def test_c() -> None:
    print("\n[C] 草稿 reject → reason → 负例 regen")
    fresh_queue()
    entry = bridge.enqueue("v1", {"platform": "x", "topic": "t"})
    q = bridge.load_queue()
    e = bridge.find(q, entry["id"])
    bridge.handle_reject(e)
    bridge.save_queue(q)
    e = bridge.find(bridge.load_queue(), entry["id"])
    check("reject 后 status=awaiting_reason", e["status"] == "awaiting_reason")
    # 模拟用户回原因
    q = bridge.load_queue()
    e = bridge.find(q, entry["id"])
    bridge.handle_regen(e, fake_hooks, reason="太营销了")
    bridge.save_queue(q)
    e = bridge.find(bridge.load_queue(), entry["id"])
    check("原因进了 rejection_reasons", "太营销了" in e["rejection_reasons"])
    check("regen 后回 pending", e["status"] == "pending")


# ═══════════════ D — 抽卡全链路 (regen bug 回归) ═══════════════
def test_d() -> None:
    print("\n[D] 抽卡 → pick → platform → playbook → 草稿持久化 + regen")
    fresh_queue()
    _reset_sent()
    batch = bridge.enqueue_cards(sample_cards())

    # pk:0  — dispatcher: load q, handle, save q
    q = bridge.load_queue()
    bridge.handle_pick(bridge.find(q, batch["id"]), 0)
    bridge.save_queue(q)

    # pf:x
    q = bridge.load_queue()
    bridge.handle_platform(bridge.find(q, batch["id"]), "x", fake_hooks, q)
    bridge.save_queue(q)

    # pb:0
    q = bridge.load_queue()
    bridge.handle_playbook(bridge.find(q, batch["id"]), 0, fake_hooks, q)
    bridge.save_queue(q)

    # ← 核心断言: 抽卡生成的草稿必须还在队列里
    q = bridge.load_queue()
    drafts = [e for e in q if e.get("kind") == "draft"]
    check("抽卡草稿持久化 (regen bug 回归)", len(drafts) == 1,
          f"队列里有 {len(drafts)} 张草稿，期望 1")
    if not drafts:
        return
    draft = drafts[0]
    # 模拟点 regen 按钮: dispatcher find(q, id)
    q = bridge.load_queue()
    found = bridge.find(q, draft["id"])
    check("点 regen 时 find 找得到草稿", found is not None,
          "找不到 → regen 无响应")
    if found:
        bridge.handle_regen(found, fake_hooks)
        bridge.save_queue(q)
        check("regen 成功执行", bridge.find(bridge.load_queue(),
              draft["id"])["status"] == "pending")


# ═══════════════ E — 全平台 ═══════════════
def test_e() -> None:
    print("\n[E] 抽卡 → 全平台 (6 平台生成 + 入队)")
    fresh_queue()
    _reset_sent()
    # mock 公众号 + 预览部署，别打真 API
    import wechat_draft
    import allplatform_preview
    wechat_draft.add_draft = lambda title, body, digest="": {
        "ok": True, "media_id": "mock_media"}
    allplatform_preview.build_and_deploy = lambda card, drafts, wx: {
        "url": "https://mock.vercel.app/preview", "local_path": "/tmp/x"}

    batch = bridge.enqueue_cards(sample_cards())
    q = bridge.load_queue()
    bridge.handle_pick(bridge.find(q, batch["id"]), 0)
    bridge.save_queue(q)
    q = bridge.load_queue()
    bridge.handle_platform(bridge.find(q, batch["id"]), "all", fake_hooks, q)
    bridge.save_queue(q)

    q = bridge.load_queue()
    drafts = [e for e in q if e.get("kind") == "draft"]
    platforms = {e["context"]["platform"] for e in drafts}
    check("全平台后 6 个平台条目全入队", len(drafts) == 6,
          f"实得 {len(drafts)}: {sorted(platforms)}")
    check("含公众号记录", "wechat" in platforms)
    check("含 5 个非公众号草稿卡",
          {"x", "linkedin", "xiaohongshu", "douyin", "tiktok"} <= platforms)
    sent_preview = any(s[0] == "send_message" for s in SENT)
    check("发了汇报消息 (含预览链接)", sent_preview)


# ═══════════════ F — 群路由 ═══════════════
def test_f() -> None:
    print("\n[F] 群路由 — TELEGRAM_GROUP_CHAT_ID")
    old = os.environ.get("TELEGRAM_GROUP_CHAT_ID")
    os.environ["TELEGRAM_GROUP_CHAT_ID"] = "-1009999"
    try:
        check("push_chat 指向群", bridge.push_chat() == "-1009999")
        check("authorized 含私聊+群",
              "-1009999" in bridge.authorized_chats()
              and str(bridge.chat_id()) in bridge.authorized_chats())
        fresh_queue()
        batch = bridge.enqueue_cards(sample_cards())
        check("batch.chat_id = 群", batch["chat_id"] == "-1009999")
        q = bridge.load_queue()
        bridge.handle_pick(bridge.find(q, batch["id"]), 0)
        bridge.handle_platform(bridge.find(q, batch["id"]), "x", fake_hooks, q)
        bridge.handle_playbook(bridge.find(q, batch["id"]), 0, fake_hooks, q)
        bridge.save_queue(q)
        draft = [e for e in bridge.load_queue() if e.get("kind") == "draft"][0]
        check("草稿继承群 chat_id", draft["chat_id"] == "-1009999")
    finally:
        if old is None:
            os.environ.pop("TELEGRAM_GROUP_CHAT_ID", None)
        else:
            os.environ["TELEGRAM_GROUP_CHAT_ID"] = old


# ═══════════════ G — push/authorized 边界 ═══════════════
def test_g() -> None:
    print("\n[G] 无群配置时回落私聊")
    os.environ.pop("TELEGRAM_GROUP_CHAT_ID", None)
    check("push_chat 回落私聊", bridge.push_chat() == str(bridge.chat_id()))
    check("authorized 只含私聊", bridge.authorized_chats()
          == {str(bridge.chat_id())})


# ═══════════════ H — comments 优化抽卡 ═══════════════
def test_h() -> None:
    print("\n[H] 抽卡 comments → 改卡标题 + 带进草稿")
    fresh_queue()
    _reset_sent()
    batch = bridge.enqueue_cards(sample_cards())

    q = bridge.load_queue()
    b = bridge.find(q, batch["id"])
    rows = bridge._card_batch_buttons(b)
    flat = [label for row in rows for label, _ in row]
    check("抽卡按钮含 Comments", "💬 Comments" in flat)

    bridge.handle_batch_comments(b)
    bridge.save_queue(q)
    b = bridge.find(bridge.load_queue(), batch["id"])
    check("点击 Comments 后等待评论", b["status"] == "awaiting_comments")

    q = bridge.load_queue()
    b = bridge.find(q, batch["id"])
    bridge.handle_batch_comment_reply(b, "卡2：把重点改成 1 星差评找新品\n整体：标题更狠")
    bridge.save_queue(q)
    b = bridge.find(bridge.load_queue(), batch["id"])
    check("comments 被保存", len(b.get("comments", [])) == 1)
    check("卡2 标题被 comments 修改",
          b["cards"][1]["title"] == "把重点改成 1 星差评找新品")

    q = bridge.load_queue()
    b = bridge.find(q, batch["id"])
    bridge.handle_pick(b, 1)
    bridge.handle_platform(b, "x", fake_hooks, q)
    bridge.handle_playbook(b, 0, fake_hooks, q)
    bridge.save_queue(q)
    drafts = [e for e in bridge.load_queue() if e.get("kind") == "draft"]
    check("草稿 context 带 comments",
          "标题更狠" in drafts[0]["context"].get("draw_comments", ""))


if __name__ == "__main__":
    for t in (test_a, test_b, test_c, test_d, test_e, test_f, test_g, test_h):
        try:
            t()
        except Exception as e:  # noqa: BLE001
            FAIL += 1
            print(f"  ❌ {t.__name__} 抛异常: {type(e).__name__}: {e}")
    print(f"\n{'='*40}\n回归结果: {PASS} 通过 / {FAIL} 失败")
    sys.exit(1 if FAIL else 0)

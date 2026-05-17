#!/usr/bin/env python3
"""
self-media 自主循环 — 每天定时跑一遍：

  1. 抽卡        5 来源聚合 → 3 张选题卡
  2. 推选题卡    整批推到 Telegram，你可以挑任意一张自己写
  3. 自动起草    挑最高分那张，套对应平台 playbook 生成草稿 + nano banana 配图
  4. 推草稿卡    直接给你一张能 Approve 的草稿

你只管在 Telegram 上点按钮。Agent 的人格 = persona.md，写法 = playbooks/。

由 launchd 触发：com.hunter.selfmedia-agent.plist（每天 09:00）。
手动跑：python3 agent_run.py
"""
from __future__ import annotations

import importlib
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "telegram-bridge"))

import gacha          # noqa: E402
import bridge         # noqa: E402
import telegram       # noqa: E402
import image_gen      # noqa: E402


def main() -> None:
    bridge.load_env()
    hooks = importlib.import_module("hooks_selfmedia")
    stamp = time.strftime("%Y-%m-%d %H:%M")
    print(f"[{stamp}] self-media agent run 开始")

    # 1. 抽卡
    cards = gacha.draw(3)
    if not cards:
        print("  没抽到候选，结束")
        return
    gacha.save_cards(cards)
    print(f"  抽到 {len(cards)} 张选题卡")

    # 2. 推选题卡批次（你仍可挑任意一张）
    try:
        bridge.enqueue_cards(cards)
        print("  选题卡批次已推送")
    except Exception as e:  # noqa: BLE001
        print(f"  推选题卡失败: {e}")

    # 3. 自动挑最高分那张起草
    top = max(cards, key=lambda c: c.get("score", 0))
    platform = (top.get("suggested_platforms") or ["wechat"])[0]
    variants = bridge.playbook_variants(platform)
    variant = variants[0] if variants else "A"
    print(f"  自动起草: 「{top['title']}」→ {platform} / {variant[:30]}")

    draft = bridge._make_draft(top, platform, variant, bridge.push_chat())
    try:
        draft["draft_text"] = hooks.generate(draft)
    except Exception as e:  # noqa: BLE001
        print(f"  起草失败: {e}")
        return

    # 4. 配图（失败不阻塞）
    try:
        out = (HERE.parent / "content" / "_covers"
               / f"agent-{time.strftime('%Y%m%d-%H%M%S')}.png")
        img = image_gen.generate_image(
            image_gen.cover_prompt(top["title"], platform), out)
        draft["context"]["image"] = str(img)
        print(f"  配图: {img.name}")
    except Exception as e:  # noqa: BLE001
        print(f"  配图失败（跳过）: {e}")

    # 推草稿卡
    q = bridge.load_queue()
    mid = telegram.send_card(bridge.token(), draft["chat_id"], draft)
    draft["telegram_message_id"] = mid
    q.append(draft)
    bridge.save_queue(q)
    print(f"  草稿卡已推送 id={draft['id']} → telegram {mid}")
    print(f"[{stamp}] 完成")


if __name__ == "__main__":
    main()

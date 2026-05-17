# super-writer

一个人的自媒体内容生产线 — 选题抽卡 → AI 写稿 → 配图排版 → Telegram 人工审核 → 多平台发布。

## 结构

- `tools/telegram-bridge/` — Telegram 审核 bridge + 各平台发布器
  - `bridge.py` — 抽卡 / 审核 / human-in-loop 长轮询主程序
  - `wechat_draft.py` — 公众号草稿 API（draft add/update/delete、深度文渲染器、本地预览）
  - `x_post.py` — X 发推 + OAuth 1.0a + 视频分块上传
  - `telegram.py` `image_gen.py` `video_gen.py`
  - `devto_publish.py` `qiita_publish.py` `youtube_publish.py`
  - `hooks_selfmedia.py` — 生成/执行 hook
- `tools/gacha.py` — 选题抽卡器（5 来源聚合 + 评分）
- `tools/agent_run.py` — 24x7 自主循环
- `tools/sources/` — 5 个选题来源采集器
- `playbooks/` — 各平台 + 各内容类型写作 playbook
- `persona.md` — 账号人设

## 凭证

所有密钥走 `~/.secrets/` 外部文件，不入库。bridge 的 `.env` 见 `bridge.py` 头部说明。

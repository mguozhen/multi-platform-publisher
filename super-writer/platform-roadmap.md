# 平台接入计划 (Platform Roadmap)

super-writer 的多平台发布矩阵 — 状态总览 + 接入路线。

## ✅ 已通 (live)

| 平台 | 工具 | 方式 |
|---|---|---|
| 公众号 | `wechat_draft.py` | 官方 Draft API（草稿箱，手动发布）|
| ~~X / Twitter~~ | ~~`x_post.py`~~ | ⛔ **暂停发布（2026-05-18 起）** — adapter 保留，全平台分发跳过 X |
| Dev.to | `devto_publish.py` | 官方 REST API |
| Qiita | `qiita_publish.py` | 官方 REST API |
| YouTube | `youtube_publish.py` | Data API v3 |
| LinkedIn | `linkedin/li-post.py` | REST API |
| 抖音 / 小红书 | social-auto-upload | 浏览器自动化（cookie 需定期刷新）|
| TikTok | TiktokAutoUploader | cli.py |

## ⚠️ 待接入 (queued)

| 平台 | playbook | adapter | 备注 |
|---|---|---|---|
| Substack | ✓ `substack.md` | `substack_*.py` 已有，未进 bridge | 英文长文 + Notes |
| note.com | ✓ `note.md` | 待建（浏览器自动化）| 日本市场 |
| Podcast | ✓ `podcast.md` | 待建（脚本口语化 + TTS + RSS）| 音频 |
| **Reddit** | 待写 | 待建 | **走浏览器自动化（Hunter 指定不走官方 API）** — 同 social-auto-upload 模式 |

## 手动

| 平台 | 备注 |
|---|---|
| 视频号 | 自动化查证不可行（创建页 SPA 在自动化浏览器不渲染），手动上传 |

## 统一接入套路

每个新平台四步:
1. 研究该平台**爆款内容** → 2. 沉淀 **playbook** → 3. 建 **publish adapter** → 4. 接进 **bridge 审核流**

## Reddit 接入要点（新列入）

- **走浏览器自动化，不走官方 API**（Hunter 明确指定）—— 同 social-auto-upload 模式,登录态 cookie + Playwright/patchright 驱动 reddit.com 发帖
- Reddit 文化铁律:**value-first，反 self-promo**。每个 subreddit 规则不同,直发广告会被秒删 / 封号
- 内容要按 subreddit 改写,标题党在 Reddit 反而扣分;走"真实分享 / 提问 / 复盘"口吻
- 与 GTM 侧已有的「Reddit Growth Agent」(见 Founder Mix Party deck) 是同一战线,可对齐

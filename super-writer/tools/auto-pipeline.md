# tools/auto-pipeline.md — 自动化运营 pipeline

> 目标：把 Hunter 每天的真实 build/对话/决策 → 自动产出 3 条草稿 → Hunter 5 分钟审 → 一键多平台分发。**人的时间预算：每天 ≤ 15 分钟**。

## Pipeline 总览

```
[日常 build/Claude对话/git commit/财务决策]
         ↓
   [00:00 cron] claude-mem 扫昨天 session
         ↓
   [00:05 cron] 调 Claude 草稿生成器 → 3 条草稿写入 content/week-XX/YYYY-MM-DD.md
         ↓
   [Hunter 每天早上 5 分钟审] → 选 1-2 条，改稿，标 ✅
         ↓
   [07:00 触发] omnichannel-publisher → X / 小红书 / 公众号
         ↓
   [07:00 触发] hyperframes + autopost.video → 视频号 / TT / YT Shorts
         ↓
   [23:00 cron] 抓当天数据写入 tracking/posts.csv
```

## 各平台分发策略

| 平台 | 形态 | 自动化程度 | 工具 |
|---|---|---|---|
| X | 纯文 + 图 + 视频 | 全自动 | `multi-platform-publisher` (Tweepy v2) |
| 小红书 | 图文笔记 (1000字+) | 半自动 (草稿 → 浏览器上传) | `multi-platform-publisher` (CDP 注入) |
| 公众号 | 长文 HTML | 半自动 (推送到草稿箱) | `multi-platform-publisher` (官方 API) |
| Substack | 英文极客长文 + Note | 半自动 (文章包 → 浏览器发布) | `tools/substack_pack.py` + `tools/substack_publish_helper.py` |
| 视频号 | 1-3 分钟横版视频 | 半自动 (草稿 → 视频号助手) | 需新建：`videohao-uploader` |
| YouTube | 长视频 + Shorts | 全自动 | YouTube Data API v3 |
| TikTok | 15-60 秒短视频 | 全自动 | 复用 `~/MKT/TiktokAutoUploader` |

## 阶段一：草稿生成器（Day 1 就要建）

### 文件：`tools/draft-generator.sh`

```bash
#!/bin/bash
# 每天 00:05 cron 触发
# 1. 拉取昨天的 claude-mem session
# 2. 调 Claude 用 persona.md + backlog.md + 昨日 session 生成 3 条草稿
# 3. 写入 content/week-XX/$(date +%Y-%m-%d).md

cd ~/self-media
DATE=$(date +%Y-%m-%d)
WEEK=$(date +%U)
mkdir -p content/week-${WEEK}

# 拉昨天的session（通过claude-mem MCP）
SESSIONS=$(claude-mem timeline --since=yesterday --format=md)

# 调用 Claude 生成（用 flatkey 代理，省钱）
echo "${SESSIONS}" | claude --persona persona.md \
  --reference backlog.md \
  --instruction "从这些session里挑3个值得发的，按 backlog 的内容公式生成草稿。每条出X中文版 + 小红书版 + 视频脚本。" \
  > content/week-${WEEK}/${DATE}.md

echo "✅ 草稿写入 content/week-${WEEK}/${DATE}.md"
```

实际实现优先级：先手动跑通一周，再写自动化。

## 阶段二：内容适配器

每条草稿 1 份源材料 → 6 种平台格式。靠 Claude 在草稿生成阶段就直接出多版本，不用后处理。

### 草稿模板（每条推文）

```markdown
## 推文 #N — [B/I/P]-[标题]

**核心信息**：[一句话浓缩]
**配图/视频要求**：[需要拍/截/录什么]
**最佳发布时间**：[X 北京时间 21:00 / 小红书 22:00 / TT 12:00]

### X (中文)
```text
[280字内，钩子 + 内容 + 钩尾]
```

### 小红书
**标题**：[20 字内带 emoji 钩子]
**正文**：[800-1500 字]
**标签**：#AI #ClaudeCode ...

### 视频脚本 (60秒)
**Hook (0-3s)**：[强钩子]
**Body (3-50s)**：[内容主体]
**CTA (50-60s)**：[关注/合作/follow]

### 公众号长文延展
**标题**：[标题党 + 直叙]
**钩子段**：[300 字内]
**主体**：[根据推文展开到 2000-4000 字]
**结尾**：[行动指令]
```

## 阶段三：发布工具链

### X — 已就绪
- `multi-platform-publisher` 已支持 Tweepy v2
- 配置：`/Users/hunter/.openclaw/config.json` 加 X_API_KEY 等

### 小红书 — 半自动
- 已有 `multi-platform-publisher` CDP 注入方案
- 必须开浏览器登录态保留
- 图片自动从草稿里挂载

### 公众号 — 已就绪
- `multi-platform-publisher` 走官方 API（appid + secret）
- 推送到草稿箱，最终发布手动 confirm（避免误发）

### Substack — 已有第一版
- 官方没有稳定公开写入 API，先采用“内容全自动 + 发布前人工确认”。
- 内容包目录：`content/substack/YYYY-MM-DD-slug/`
- 创建文章包：
  ```bash
  python3 tools/substack_pack.py \
    --idea "I built an academic Agent that can argue back" \
    --context /Users/hunter/ai-researcher \
    --context /Users/hunter/论文
  ```
- 发布前复制：
  ```bash
  python3 tools/substack_publish_helper.py <article-dir> --copy title
  python3 tools/substack_publish_helper.py <article-dir> --copy subtitle
  python3 tools/substack_publish_helper.py <article-dir> --copy post
  python3 tools/substack_publish_helper.py <article-dir> --copy tags
  ```
- 可加 `--open` 打开 `https://substack.com/`。
- 红线：默认不自动点击 Publish。浏览器自动化最多停在预览页，最终发送由 Hunter 确认。

### 视频号 — 缺工具，需要建
- 视频号助手网页端 + CDP 注入
- 工具 backlog：`tools/videohao-uploader/` (Day 7 之前必须 ship)
- 备选：先发到公众号视频，复用同一份 mp4

### TikTok — 复用 ~/MKT
- 已有 `TiktokAutoUploader` (~/MKT)
- 中文版改账号 Cookie

### YouTube — 新增
- YouTube Data API v3
- Shorts 走 `#shorts` tag 自动识别
- 视频从 hyperframes / autopost.video 输出

## 阶段四：内容生产工具链

### 视频内容
- **短视频 demo**：hyperframes skill 直出，加 Hunter 配音（ElevenLabs / 自录）
- **过 TT 审核**：autopost.video pipeline (Seedance I2V + humanize)
- **猫先生 IP**：JP TikTok 复用 ~/MKT 整套
- **录屏 demo**：macOS QuickTime 录屏 + ffmpeg 加字幕

### 图片
- **架构图**：用 mermaid + 截图
- **代码截图**：carbon.now.sh / Ray.so
- **小红书封面**：Canva 模板 + Hunter 头像
- **配图统一**：用 `image-poster` skill 出主视觉

## 阶段五：数据追踪

### tracking/posts.csv
```csv
date,platform,post_id,topic_id,category,title,impressions,engagement,followers_delta,note
2026-05-11,X,123456,B1,Build,wx-schedule 4小时打通,1500,80,15,首条
```

每天 23:00 cron 抓数据写入。所有平台 API 拿不到的，半自动用 CDP 抓。

### tracking/followers.md
每周一更新 6 平台粉丝数曲线 + 本周复盘。

## 关键依赖

- ✅ `multi-platform-publisher` Python skill — Twitter/LinkedIn/WeChat/小红书
- ✅ `omnichannel-publisher` skill — 跨平台调度
- ✅ `hyperframes` — 视频生成
- ✅ `autopost.video` — TT 审核通过的 AI 视频
- ✅ `claude-mem` MCP — session 扫描
- ✅ `flatkey.ai` — LLM 代理（省钱）
- ⏳ `videohao-uploader` — 视频号自动化（需建）
- ⏳ YouTube API 接入（需建）

## 第一周执行清单

- [ ] Day 1：手动发第 1 条（B1 wx-schedule），跑通 X + 小红书 + 公众号
- [ ] Day 2：手动发第 2 条（P3 元推文 / 开账号宣言）
- [ ] Day 3：跑通视频号 + TT 上传，发 B4 (autopost.video)
- [ ] Day 4：建 draft-generator.sh 雏形，跑一次
- [ ] Day 5：YT 频道开通 + Shorts 流程跑通
- [ ] Day 6：搭 tracking/posts.csv 自动化
- [ ] Day 7：第一周复盘 → 微调 persona

## 红线

- 自动发布前**必有人确认环节**（公众号必须，因为不可撤回）
- 跨平台同一时段错峰：X 21:00 / 小红书 22:00 / 公众号 08:00 / 视频号 19:00 / TT/YT 灵活
- 每个平台**至少前 10 条手动发**，跑通账号权重再上自动化

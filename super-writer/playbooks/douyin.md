# 抖音 Playbook

> 平台: 抖音 (中文短视频)
> 工具: autopost.video (~/autopost.video)
> 爆款参考: Simon林「Claude Code x Qlib：量化研究」= Claude Code + 具体技术栈实操

## 核心定位

中文 AI 实操视频。不是炫技，是「我用 Claude Code/Codex 做了一件具体的事」。
爆款公式 = Claude Code × 一个具体垂直场景（量化 / 客服 / 视频 / 数据）。

## 三种 playbook 变体（发之前选一个）

### variant A — 工具实操演示（推荐，对标 Simon林）
一个具体技术任务，全程录屏 + 中文配音。
```
时长: 60-90 秒
结构:
  0-3s   钩子: 一句话 + 结果前置  "用 Claude Code 4 小时做了个量化工具"
  3-50s  过程: 加速录屏，关键步骤
  50-60s 结果: 跑出来的东西 + 一句总结
规格: 1080×1920, 30fps
```

### variant B — 行业观点口播
对镜头讲一个 AI 行业判断。
```
时长: 30-60 秒
真人出镜 / 或 autopost.video 生成
字幕必须有（静音播放占多数）
```

### variant C — remix 爆款
从抖音爆款 remix（autopost.video arbitrage pipeline）。
```
autopost.video: cli.orchestrator.arbitrage <抖音URL> --mode regen
```

## autopost.video 生产链路

```
输入: 选题 / GitHub 项目 / 抖音 URL
  ↓
cli.orchestrator.arbitrage 或 regen pipeline
  ↓
1080×1920 mp4 → humanize.py (过审) → fix_violation.py
  ↓
Telegram 预览卡 → Hunter approve
  ↓
cli/utils/douyin.py 上传
```

## tone 规则

- 中文配音 (edge-tts 或 F5-TTS)
- 钩子前置（0-3 秒定生死）
- 字幕烧死（PIL）
- 标题带技术栈关键词（Claude Code / 量化 / Agent）

## 禁区

- ❌ 标题党词「炸裂」「震惊」（抖音也压）
- ❌ AI 痕迹太重（必过 humanize）
- ❌ 政治 / 金融建议

## 发布

```
autopost.video 生成 → Telegram 审核 → douyin 上传
时间: 中文圈晚间 19:00-22:00
cookie: scripts/refresh_douyin_cookie.sh 定期刷新
```

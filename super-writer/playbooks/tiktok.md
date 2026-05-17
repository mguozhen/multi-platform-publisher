# TikTok Playbook

> 平台: TikTok (英文短视频, 海外)
> 工具: autopost.video + ~/MKT/TiktokAutoUploader
> 角色: 海外爆发

## 核心定位

英文 AI 实操短视频。海外 dev / builder 受众。
「Chinese SaaS chairman builds with AI」这个生态位英文圈空白。

## 三种 playbook 变体（发之前选一个）

### variant A — build demo（推荐）
30 秒工具演示，英文配音/字幕。
```
时长: 15-30 秒
0-2s   hook: "this saves me 3 hours every day"
2-25s  demo: 屏幕录屏，操作快
25-30s CTA: 关注引导
规格: 1080×1920, 30fps
```

### variant B — 从抖音版翻译
抖音视频走 translate_dub pipeline 转英文。
```
autopost.video: cli.pipelines.translate_dub
中文 → Whisper ASR → Qwen 翻译 → edge-tts 英文配音
```

### variant C — 行业 hot take
英文口播一个 AI 观点。
```
时长: 20-40 秒
```

## autopost.video 生产链路

```
输入: 选题 / 抖音中文版 / 英文脚本
  ↓
translate_dub (中→英) 或 regen (新生成)
  ↓
humanize.py (破 TT AI 检测) — 必跑
  ↓
1080×1920 mp4
  ↓
Telegram 预览卡 → Hunter approve
  ↓
cli/utils/tiktok_publish.py → ~/MKT/TiktokAutoUploader
```

## tone 规则

- 英文，简短直接
- hook 0-2 秒
- 字幕必须（TT 80% 静音播放）
- 标签 3-5 个: #AI #ClaudeCode #BuildInPublic
- humanize 必跑（不然被标 AI / 非原创）

## 禁区

- ❌ 不出现 "Twitter/X" 字眼（跨平台导流被压）
- ❌ 不挂 wx/微信
- ❌ ChatGPT/Claude 字幕模糊处理（限流敏感词）

## 发布

```
autopost.video translate_dub → humanize → Telegram 审核 → TT 上传
时间: 北美黄金 (北京次日 13:00-15:00)
账号: TiktokAutoUploader 需 TT cookie
```

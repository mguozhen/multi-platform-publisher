# Dev.to Playbook

> 平台: Dev.to（全球开发者社区）
> 账号: Hunter G
> 发布: 官方 REST API 直连（`devto_publish.py`）
> 语言: **100% Native English**（polished, geeky, 不要中式英语、不要 AI 腔）

## 爆款规律（2026-05 实测热门文研究）

抓了 Dev.to 30 天 top 文，能复刻的爆款分 4 类：

1. **强观点 hot-take** — 「I Love Tailwind. Sorry Not Sorry」169❤。一个有人爱有人恨的技术立场，标题就把刺挑明。
2. **AI 时代个人反思** — 「I Used to Love Coding. Now I Just Prompt.」「I Didn't Stop Building. I Just Left My Laptop.」第一人称、情绪真实、戳行业集体焦虑。
3. **实用 listicle** — 「15 Essential Sections Every README Needs」156❤。数字 + 干货清单。
4. **discuss 引战** — 「If AI Existed in 2011, Would We Still Have the Modern Web?」198❤ 143💬。开放性问题，逼人评论。

共性：第一人称、标题就是钩子、AI/career/webdev 是流量池、评论数 > 点赞数才算真火。

## 三种 variant

### variant A — AI 时代个人反思（推荐，最高 ROI）
我作为一个 build AI 产品的人，对这个行业的真实感受 / 转变。
```
例: I Stopped Hiring Engineers. I Just Ship With Claude Code Now.
结构: 一个具体场景钩子 → 我的转变 → 数据/产品佐证 → 给同行的判断
tags: ai, career, productivity, webdev
```

### variant B — 开源项目 / skill 介绍（英文版）
把 voc-amazon-reviews 这类开源项目讲给全球开发者。
```
例: I Open-Sourced an Amazon Review MCP Server — The Data Is the Moat
结构: 反常识问题 → 项目 → demo → install → repo 链接
tags: opensource, ai, showdev
```

### variant C — 实用 listicle
N 条可执行清单。
```
例: 11 Things I Learned Shipping 12 AI Products Solo
tags: programming, productivity, ai
```

## 铁律

- 英文必须 native，模仿 Jesse Zhang 那种克制高管语气：human, specific, modest, low-hype
- 标题第一人称 + 钩子，禁标题党震惊体
- ≤4 个 tag，全小写无空格；首发用 `published=false`（草稿）→ 审核后再上线
- body 是 markdown，代码块 / 列表正常用
- 配图用真实截图（GitHub / terminal），不 AI 发散生成

## 发布

```
devto_publish.publish(title, body_md, tags=[...], published=False)
```

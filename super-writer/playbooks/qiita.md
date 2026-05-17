# Qiita Playbook

> 平台: Qiita（日本最大开发者社区）
> 账号: mguozhen（已有 17 篇）
> 发布: 官方 REST API 直连（`qiita_publish.py`）
> 语言: **全日文极客版**（带 diff / code / note，自动翻译后人审）

## 爆款规律（2026-05 实测高 LGTM 文研究）

抓了 Qiita 高 stock 文，规律非常清晰：

1. **Claude Code / AI 駆動開発 是当下绝对顶流** — 「Claude Code を Level 5 まで育てたら」686、「Claude Code 完全リファレンス」376、「Agent に入れるべき Skills 20選」371、「100行のCLAUDE.mdより35行が効く理由」533。Hunter 的内容（Claude Code + skill + 11 个 AI 产品）天然踩中。
2. **完全版 / 完全リファレンス / 図解** — 「完全リファレンス」「【図解】設計思想の進化」。日本读者爱「一篇打包讲透」+ 图解。
3. **ポエム（随笔/职业故事）狂吸赞** — 「エンジニア歴20年の私が物申す」**2161 LGTM**、「あいつには関わりたくない2年間」1141。情绪真实的职业自述。
4. **初心者完全版 教程** — 「0からNext.js 2時間でマスター【図解解説】」。

共性：【】方括号标题、完全版/完全リファレンス、図解、初心者 framing、ポエム 情绪。

## 三种 variant

### variant A — Claude Code / skill 深度文（推荐，踩中顶流）
把 Hunter 用 Claude Code + 自制 skill 的实战，做成「完全リファレンス」式。
```
例: 【完全ガイド】Claude Code で AI 製品を 12 個 個人開発した方法
tags: ClaudeCode, AIエージェント, AI駆動開発, 個人開発
体裁: 図解 + 实文件结构 + 便利機能トップ N
```

### variant B — 开源项目 / skill 介绍（日文版）
voc-amazon-reviews 这类，讲给日本开发者。
```
例: 【OSS】Amazon レビュー分析 MCP サーバーを公開した — 強いのはデータ層
tags: MCP, OSS, AI, Amazon
```

### variant C — ポエム（职业随笔）
经营三个 AI 公司 / solo 跑 12 个产品的真实感受。
```
例: 「董事長」という仕事を AI に作り直してもらった話
tags: ポエム, AI駆動開発, キャリア
```

## 铁律

- 全日文，技术术语用日本开发者习惯的说法（不要生硬机翻腔）
- 标题善用【】方括号 + 完全版/完全ガイド/図解
- tags 用 Qiita 实际热门标签：ClaudeCode / AIエージェント / AI駆動開発 / 個人開発 / プロンプトエンジニアリング
- 首发用 `private=true`（限定公开）→ 人审日文后再公开
- 代码、diff、図 正常用，日本读者吃这套

## 发布

```
qiita_publish.publish(title, body_md, tags=[...], private=True)
```

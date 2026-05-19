# Hacker News Playbook

> 平台: Hacker News（news.ycombinator.com）
> 工具: `hn_publish.py`（浏览器自动化，HN 无 submit API）
> 风格: value-first，反 self-promo 极严

## ⚠️ 铁律（违反 = 沉到 dead / shadowban）

- **绝不进例行全平台批量**。每一篇值得发的，单独人工评估 + 单独发。
- **绝不带营销语气**。「我做了 X」远好过「来用我做的 X」。
- **submission ≠ blog post**。HN 标题要客观、不情绪化，钩子在内容里不在标题里。
- **不要回应「Show HN: ...」式炒作钩子**，除非你真的在 ship 一个独立可玩的东西。
- 同账号一周不发超过 1 条 self-link，否则被 flag。
- HN 用户对 AI 包装的「自媒体工具 / 内容农场」反感度极高 —— 这类项目最好不发。

## 三种 variant（选 1，否则别发）

### variant A — Show HN（自己 ship 的开源工具）
真正 ship 出去、能跑、有看头的东西。
```
标题: Show HN: <project> – <one-line factual description>
  例: Show HN: voc-amazon-reviews – MCP server that turns an ASIN into a VOC report

正文（首条评论里写）:
  - 2-3 段，第一段说项目做什么 + 你为什么做
  - 一段技术决策的"奇怪选择"（最易拿评论）
  - GitHub 链接放评论顶部，repo 必须 README 完善
长度: 正文 < 200 词
```

### variant B — Ask HN（向社区取经）
开放问题，要真有疑问。
```
标题: Ask HN: How do you <specific question>?
  例: Ask HN: How do you debug long-running agent loops in production?
铁律: 别在正文偷塞产品；HN 用户秒识破
```

### variant C — 技术 deep-dive 长帖
不带产品、纯技术发现。如 "I rewrote our scheduler in Zig and lost 40% throughput, here's why"。
```
标题: 客观陈述，避免感叹号 / "I learned ..."
正文: 链接到自己的 blog post（非营销页）
```

## 标题铁律（生死线）

- 全小写或正常标题大小写 —— 绝不全大写
- ≤ 80 字符（HN 截断）
- 不带 emoji，不带「🚀 launch」「Introducing X」这类
- 不带数字党：「I 10x'd my X」「How I got 1000 users」
- 客观、具体、有信息量。「Show HN: voc-amazon-reviews – ASIN → VOC report (MIT)」 优于 「I open-sourced my Amazon review tool!」

## 第一条评论（自带）

发完立刻自己回一条评论:
- 1-2 段 context: 为什么做 / 现状怎么解决 / 你的项目差在哪
- 一个具体的「奇怪决策」邀请讨论（例:「为什么我选 shell 而不是 Python」）
- 不带任何 CTA / 不喊 star
- GitHub 链接已在标题或正文里挂了，评论里不重复

## 发帖时机

- 美东周二/周三/周四上午 08:00–10:00 ET（前 90 分钟决定能否上首页）
- 周末不发，重大新闻日不发（被淹）
- 一次只发一个项目，别同时发多条

## 不发的情况（明确放弃）

- 「我做了一个自媒体发布工具」 →❌HN 用户反感这类
- 「AI agent for X」类已饱和 → 除非有非常具体的技术突破
- 工具是包装外部 API（不是真正的技术深度）→ ❌

## 发布

```bash
python3 ~/self-media/tools/hn_publish.py --title "Show HN: ..." --url https://github.com/...
# --auto-publish 才会真的提交；否则停在 submit 表单等你点
```

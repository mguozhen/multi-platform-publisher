# Reddit Playbook

> 平台: Reddit（按 subreddit 调性发，不是一篇打天下）
> 工具: `reddit_publish.py`（浏览器自动化，按 Hunter 指定不走官方 API）
> 风格: value-first，反 self-promo 极严（同 HN）

## ⚠️ 铁律（违反 = 删帖 / 封号 / shadowban）

- **每个 subreddit 规则不同** —— 发之前读 sidebar + recent 10 条置顶 post，了解禁区
- **绝不进例行全平台批量** —— 一次一个 subreddit，单独评估
- **9:1 法则** —— 你在该 subreddit 的发帖里，9 条是回答别人 / 评论 / 分享别人的，1 条才能是自己的项目
- **新号 / 低 karma 直发 self-link → 秒删**。先在该子版积累 50+ comment karma 再投
- **不要标题党 / 震惊体**。Reddit 用户对 clickbait 反感度极高

## 适合发的 subreddit（按 multi-platform-publisher 这类工具评估）

| subreddit | 调性 | 能不能发 |
|---|---|---|
| r/SideProject | 友好，欢迎独立项目 | ✅ 优先 |
| r/opensource | 欢迎 OSS，要求项目真实 | ✅ |
| r/SaaS | founder 圈，工具友好 | ✅ |
| r/Entrepreneur | 大杂烩，文章风格要谦逊 | ⚠️ 容易被划水 |
| r/programming | 极严，仅技术深度 | ❌ self-promo 必删 |
| r/MachineLearning | 极严，仅 paper / 真硬技术 | ❌ |
| r/LocalLLaMA | 友好但要技术含量 | ⚠️ 需配 LLM 角度 |
| r/AI_Agents | 新兴友好 | ✅ |

## 三种 variant

### variant A — "I built X" 复盘（最稳）
个人叙事 + 真实数字 + 给同类用户的建议。
```
标题: I built <X> after I got tired of <pain>. Here's what I learned.
  例: I built an open-source multi-platform publisher after timing my own workflow at 90 minutes/post

结构（正文 300-500 词）:
  - hook: 一个具体场景，不夸张
  - 你做了什么 + 几个具体决策
  - 1-2 个意外发现 / 教训
  - GitHub 链接放最后一行
铁律: 全程谦逊，"this might be wrong but..."
```

### variant B — "Show me yours" 引发讨论
带着自己的工具问别人怎么做。
```
标题: How do you handle <pain>? I built <X>, curious what you use.
正文: 描述自己的方案 1 段 → 真诚问别人方案
```

### variant C — value-first 教程
免费给读者一个完整可跑的 how-to，工具是教程里的工具之一（不是主角）。
```
标题: How to <do useful thing> in <small time>
正文: 真教程，工具链里你的项目作为其中一环
```

## 标题铁律

- 客观、具体、有信息量
- ≤ 100 字符
- 不带 emoji
- 不带「🔥」「Just launched」「Game changer」这类
- 不写「I made the best X」—— 写「I made an X that does Y」

## 正文格式

- 第一段 hook，3-5 行内
- 用 markdown headers（##）分节，Reddit 支持
- 代码块用 ``` 包
- GitHub 链接：variant A 放最后；variant B/C 放正文里有 context 的地方
- 不写「DM me」「Check my bio」—— 反 spam 雷区

## 发帖时机

- 美东周一/周二/周三 09:00–12:00 ET
- 周五 / 周末参与度高但批评多
- 重大新闻日不发

## 发完之后

- 头 30 分钟必须守着评论区，秒回前 3-5 条
- 评论里不要狂赞自己 / 不要让朋友刷赞，会被检测
- 被怼的话，技术性回应、不情绪化、不删评论

## 发布

```bash
python3 ~/self-media/tools/reddit_publish.py <article_dir> --subreddit SideProject
# article_dir 里要有 post.md（正文）+ meta.md（## Primary Title）
# 工具会停在 submit 页等你点 Post（不会自动发，HN/Reddit 风险太高）
```

# LinkedIn Playbook

> 平台: LinkedIn (英文, 全球 founder / SaaS / 投资人圈)
> 工具: li-post.py (OAuth)
> 角色: 商业信用 · 海外 founder 网络

## ⚠️ 全英文铁律

LinkedIn **正文 + 配图都必须英文**。绝不能把中文平台（公众号/小红书）的中文封面
复用到 LinkedIn 帖子上。做多平台时单独渲染英文封面（参考 cover_en.png 模式）。

## 核心定位

LinkedIn 看的是「商业判断」。Hunter 的优势：真在跑 SaaS 集团的董事长视角，
比纯 dev 测评稀缺。观察者姿态 > 受害者姿态。

## 三种 playbook 变体（发之前选一个）

### variant A — Founder 行业观察长贴（推荐）
一个行业事件 → 三类分析 → 给从业者的判断。
```
结构:
  hook (前 2 行, 决定算法推不推):
    [一句反差断言]
    [一句"如果你是 X，往下看"]
  body (~280 词):
    - 现象 + quick math
    - 分 3 类: 谁活 / 谁死 / 怎么办
    - 不抱怨，给判断
  收尾: 一句命令式 + 署名
长度: 250-320 词
```

### variant B — Build 复盘短贴
ship 了什么 + 对 founder 的启发。
```
长度: 100-150 词
hook → 做了什么 → 1 个可迁移的 takeaway
```

### variant C — 决策透明贴
公开一个集团决策（财报/激励/并购）。
```
长度: 200-280 词
风险: 真实数字需先脱敏
```

## 推广开源项目（2026-05-18 实战定型，过审版）

发开源项目一律走 **variant A 观察姿态**，不做产品 pitch：
- hook 用一个反差数字 / 断言（例：写一篇文章 60 分钟，发出去 90 分钟），不是「我做了个工具」
- 工具是观察的**落点**，不是主语 —— 正文重心是一个判断（哪半工作是 tax），工具只在后段登场
- 收尾落在原理（「执行变便宜 → 把 tax 那半交出去」），命令式，不在正文喊「去 star」

链接铁律（这是关键）：
- **GitHub 链接绝不进正文** —— LinkedIn 算法压站外链接帖，曝光腰斩
- 链接放**第一条评论**：发完用 `socialActions/{share}/comments` API 补 comment
  （`li-post.py` 不支持发评论，需单独调 API：`POST /v2/socialActions/{urlencoded-share-urn}/comments`，body `{actor, message:{text}}`）
- 求 star 的话也放进第一条评论，不放正文

## 排版规则（LinkedIn 算法）

- 前 2 行是生死线（折叠前可见）— 必须是 hook
- 每 1-2 句一段，大量空行（手机可读性）
- 不要 markdown 符号（LinkedIn 不渲染 **bold**）
- 用 → 箭头、• 圆点做视觉分层
- 3-5 个 hashtag 放结尾

## tone 规则

- 英文，专业但不端着
- 第一人称，敢下判断
- "I'm publicly admitting X" 这种透明度是稀缺资产
- 不卖课、不挂链

## 禁区

- ❌ 不堆头衔（让内容说话）
- ❌ 不写 "Thoughts?" 求互动（廉价）
- ❌ 不政治

## 发布

```
source ~/.secrets/linkedin.env
python3 ~/self-media/tools/linkedin/li-post.py "内容" --image 图
时间: 美东上班时段 (北京 21:00-23:00)
```

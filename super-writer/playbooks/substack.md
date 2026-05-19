# Substack Playbook

> 平台: Substack — 英文长文 newsletter + Notes（短内容社交层）
> 定位: Hunter 的英文 founder essay 阵地，对标 Lenny's Newsletter / Noahpinion 的深度
> 频率: 长文每周 1-2 篇 + Notes 每天 1-3 条

## 平台特性（2026 实测）

- 头部全是**深度分析型** newsletter（Letters from an American 290万订阅、Lenny's $2M/年、Noahpinion）。头部财经号一周发 11+ 篇深稿。
- 两个内容层:
  - **长文 (Posts)** — newsletter 正文，深度 essay，发到订阅者邮箱
  - **Notes** — 短内容社交流，是涨粉入口，机制类似 X

## 长文 (Posts) 怎么写

- 英文。深度 essay，对标 Lenny / Stratechery：一个观点 → 层层论证 → 可执行收获
- 题材直接复用公众号 variant B/C/G（调查复盘 / 决策自白 / 工具对比）的英文版
- 开头不寒暄，第一段就给钩子或反常识结论
- 给真实数据、真实经历、具体数字 —— Substack 读者付费，吃深度不吃水文
- 结尾留一个 forward-looking 判断

## Notes 怎么写（涨粉主力，爆款机制）

实测规律（分析 19000+ 爆款 Notes）:
- **情绪清晰 > 精致**。爆款不是最打磨的，是最"暴露"的那篇
- **微故事 + 转折**:< 300 字的小故事，从故事中段切入钩住读者，收束到一个"啊哈"洞察
- **短**:爆款 Notes 普遍 150-360 字，越短越易传播；能在 150 字内触达情绪核心最好
- **高唤醒情绪**:让人笑 / 鼻酸 / 被看见 / 被点燃 —— 情绪强度决定转发
- 制造反差，加一个奇怪的形容词，让读者"有点不舒服"才会有感觉
- Notes 钩 → 长文转化 → 订阅

## Hunter 适配

- 英文写作，硅谷前沿 AI 公司定位
- 长文 = 公众号深稿的英文重写（一个人跑 11 个产品 / cc vs openclaw / AI-Native 实践）
- Notes = 从长文里切金句 + 微故事，每天投放
- ❌ 不写水文、不写"AI 帮你"泛泛而谈；Substack 读者最挑深度

## 爆款长文型（蒸馏自 Jimmy's Journal「Deep Dive: Veeva Systems」, paid 长文）

Substack 头部 paid 长文有一套近乎模板化的结构，**踩这个结构本身就提升完读+订阅**：

1. **品牌问候 hook** —— 第一行 `Hi, <角色称呼>! 👋🏼` 或类似（不是直接进主题）。比如 `Hi, Investor!` / `Hi, Builder!` 这种点名读者身份的，比「Welcome」更有钩感。
2. **元层观察（不是主题本身）** —— 第二段不讲产品/事件本身，先讲一个**关于该话题的元观察**（如「Markets have an ugly habit of acting first and understanding later」）。让读者觉得作者站得更高。
3. **「这次说什么」段** —— 用 1-2 句明确这篇要拆 5-6 个维度（"In this deep dive, we'll break down..."），让读者预期完整。
4. **修辞钩问句** —— 紧跟一句反差大的「A 还是 B?」（如 "Are we looking at a generational opportunity, or does the bottom of this hole have a trapdoor?"）。
5. **品牌植入板块** —— 一个独立短段 "Welcome to <Newsletter name>, your one-stop shop for <X>." + 一句作者背书 + 一个 Subscribe 按钮（Substack 编辑器自带）。
6. **"In case you missed it"** —— 列 2-3 篇过往文章内部链接（养老用户阅读链），新号没存量可先省略。
7. **章节大纲** —— "Today's post is longer than usual, so we've included an outline below:" + 15-20 个 H3 小节列表。这一招提前承诺深度，长文不再吓退人。
8. **编号 H2 章节** —— `1. Overview` / `2. Business Model` / `3. ...` 每节带数字，最后一节固定是 `Final Thoughts` 或 `Investment Thesis`。
9. **Source 出处行** —— 凡引图/数据，下面单独一行 `Source: <出处>, <年>`。建立信任。
10. **段间留白，单句成段** —— 几乎每一句都独立成段。Substack 长文是手机/邮箱阅读，长段就是死。
11. **付费/订阅卡前置 + 末尾再来一次** —— 中段插一次「Subscribe now and start compounding.」按钮，末尾再插一次。
12. **无 emoji 滥用** —— 全文除 hook 那个 👋🏼 外不用 emoji。表情清淡 = 严肃感。

→ **这个结构适配 OSS 发布 / 深度复盘 / 行业观察都通**，只需把「Investment Thesis」「Valuation」换成「Architecture」「Adoption」之类的。

## 发布

- `tools/substack_browser_publish.py` —— 浏览器自动化全自动发布（用 `.chrome-substack-profile` 登录态）
- `tools/substack_publish_helper.py --copy` —— 半自动，复制各段到剪贴板手贴
- 长文进 draft → 人工审核 → 发布

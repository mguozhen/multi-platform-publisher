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

## 发布

- `tools/substack_*.py` 已有 Substack 发布工具（浏览器自动化）
- 长文进 draft → 人工审核 → 发布

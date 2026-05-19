# Principle — Agents 是新的分发渠道，做能力，不做界面

> 业务 / 产品设计核心原则。可直接粘进任何 Agent playbook。
> 也是内容价值锚点 —— 尽量在所有文章里体现（见 memory `reference_ai_native_viewpoint.md` 锚点 6）。

**原则。** 外部 AI Agent 是和当年 App Store、当年 SEO、当年微信公众号同量级的新分发渠道。Agent 在调用的不是你的 UI，是你的能力。如果你的产品只有界面没有 API，Agent 就绕过你；如果你的 API 不 agent-friendly，Agent 就选别人。

**为什么成立。** 用户行为正在从「打开 App」切到「让 Agent 办事」。Agent 替用户做决策、做调用、做支付。它不会读你的落地页，不会点你的按钮，它只读你的 OpenAPI / MCP / Tool schema。谁先成为 Agent 默认调用的那个能力源，谁就拿到这波分发红利。

**它改变了什么决策。**

1. **每个核心能力都必须先有 API，再有 UI。** 没有 API 的功能等于不存在。
2. **API 的设计语言对象是 Agent，不是前端工程师。** 描述清晰、错误自解释、参数最少、副作用可预测。
3. **支付 / 结算 / 订阅这种「非做不可」的环节，要主动让 Agent 找得到、调得通、记得住。** 简单到一次 tool call 就能完成，不要让 Agent 还得跳浏览器。
4. **下周必做的最简单升级：让你现有 API 变成 agent-friendly** —— OpenAPI 文档齐、错误码语义化、auth 不依赖 cookie、有 MCP wrapper。

**反例。** 你做了一个好功能但藏在 SaaS dashboard 第 3 层菜单后面，Agent 永远调不到 → 这功能在 Agent 时代不存在。

# 量子位（QbitAI）公众号排版 Playbook
量测来源：《刚刚，Claude Code大重构！内部3万Agent管理技术免费开放》(mp.weixin.qq.com/s/w4LCCflzIoWYWFQf2asBwg)，2026-09，逐元素 computed inline style 实测。

## 数值系统（全部实测，非感觉）
| 元素 | 参数 |
|---|---|
| 正文段落 | `font-size:16px; color:rgb(34,34,34); font-family:Arial; line-height:2; letter-spacing:1px; word-spacing:1px; margin:20px 16px; text-align:left` |
| 高亮（划重点） | `<strong><span style="font-weight:bold;color:rgb(0,153,127)">` 绿色加粗，全文 15 处，密度约每 5 段 1 处 |
| 小标题 H2 | `font-size:20px; font-weight:bold; line-height:1.5; margin:40px 0; padding-left:15px; border-left:6px solid rgb(0,153,127); letter-spacing:1px` 绿色左竖条 |
| 图注 | `font-size:14px; color:rgb(136,136,136)` 居中；极小注 12px |
| 划线/分隔条 | `height:5px; background-image:linear-gradient(90deg, rgba(0,153,127,.5) 13%, rgba(235,25,24,0) 100%)` 外层 `rotateY(180deg)`（向左淡出），用于尾部分隔 |
| 品牌绿 | `rgb(0,153,127)` 一个颜色贯穿：高亮、H2 竖条、渐变条、尾部行动号召 |
| 头部署名 | 「XX 发自 凹非寺」灰 + 「量子位 \| 公众号 QbitAI」绿，各自一行，14px |
| 尾部固定块 | 右对齐：`一键三连` 黑粗 + `「点赞」「转发」「小心心」` 绿粗 + `欢迎在评论区留下你的想法！` 黑粗；上方放渐变条 |
| 图片 | `margin:0 auto` 居中通栏，配图以真实截图为主（产品界面/推文/文档），不是概念插画 |

## 文风节奏
- 开头 1-3 段是钩子，每段一两句话，直接抛最大的事实/数字；常用「刚刚，」开场
- 全文短段落，一句一段很常见；转折用口语（"没错""注意""换句话说"）
- 每节 1-2 个绿色加粗句 = 读者划重点的地方；加粗的是**结论句**不是名词
- 小标题是事实/数字型（"26%的研发交给AI，半年飙升26倍"），不是悬念型
- 结尾常带 One More Thing 或互动引导

## 渲染器
`~/self-media/tools/build_wechat_qbit.py`：article.md → 上述系统的公众号 HTML。
约定：`**粗体**`→绿色高亮；`## `→绿左条 H2；`![](path)` 下一行若是 `*图注*` → 灰色居中图注；文末自动追加渐变条+一键三连块；`---` 后的内容渲染成 14px 灰色小字（参考来源/利益相关）。

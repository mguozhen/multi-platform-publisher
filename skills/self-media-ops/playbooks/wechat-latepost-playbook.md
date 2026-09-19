# 晚点 LatePost（晚点再听LaterCast）公众号排版 Playbook
量测来源：《为什么 Agent 的运行框架，比模型本身更重要？丨Y Combinator》(mp.weixin.qq.com/s/8BioVF6EmSi3zV9_Mm6Gnw)，2026-09，逐元素 inline style 实测。
**状态：新闻类文章的默认 playbook（2026-09-18 起，Hunter 指定）。**

## 数值系统（全部实测）
| 元素 | 参数 |
|---|---|
| 字体栈 | `-apple-system, BlinkMacSystemFont, 'PingFang SC', 'Helvetica Neue', 'Microsoft YaHei', sans-serif`（系统栈，非 Arial） |
| 正文段落 | `font-size:16px; line-height:2em; margin-bottom:20px; text-align:left`，颜色默认黑 |
| 品牌黄 | `rgb(252,220,112)` 一种颜色三种用法：标题荧光、引语荧光、引用块左条 |
| 小标题 H2 | `font-size:22px; font-weight:600; line-height:1.6em; text-align:center; margin:40px 0 20px`，文字外包一层 `<span style="background-color:rgb(252,220,112)">` = **居中黄底荧光标题** |
| 引语高亮 | `<span style="background-color:rgb(252,220,112); font-style:italic">` 黄底+斜体，专用于**直接引语**（带引号） |
| 引用块 | `font-size:15px; color:rgb(85,85,85); border-left:4px solid 黄; padding-left:12px; margin:24px 0; font-style:italic; line-height:2em; background:#fff` |
| 加粗 | `<strong>` 纯黑粗体，加的是**机制结论句**（"权重没有变，工具、记忆和运行方式变了…"） |
| 图注 | `font-size:12px; line-height:1.6em; text-align:center; color:rgba(0,0,0,.5)`，**图注是分析句不是标签**（"多人共用 Agent 时，哪些信息可以共享…需要权限系统明确约束"） |
| 栏目导语 | `font-size:14px; color:rgba(0,0,0,.6); line-height:1.75em`，文首一段固定栏目说明 |
| 链接色 | `rgb(87,107,149)` 蓝灰 |

## 结构与文风
1. **栏目导语**（14px 灰）一段
2. **金句前置**：正文开始前先甩 2-3 条黄底斜体直接引语，无上下文，制造钩子
3. **场景化导入**：一两个具体小故事/画面（"工程师挨台登录虚拟机修问题"），不加评论
4. 主体分节：居中黄底 H2；每节 16px 长段落（比量子位长，一段 3-5 句，讲机制）；黑粗结论句；黄底引语穿插
5. 语言：克制、白描、准确到数字（"3.2 个百分点，成本差距仅对应图中实验配置"），不用感叹号，几乎零口语转折——**跟量子位相反**
6. 标题式样：`陈述句/问题句丨来源`（「为什么 Agent 的运行框架，比模型本身更重要？丨Y Combinator」）——问题句允许，但仍是事实型不是悬念型

## 渲染器
`~/self-media/tools/build_wechat_latepost.py`：article.md → 上述系统。
Markdown 约定：`%% 文字`→栏目导语；`==文字==`→黄底斜体引语；`> 文字`→黄左条引用块；`**粗**`→黑粗；`## `→居中黄底 H2；图片下一行 `*…*`→12px 分析型图注；`---` 后→14px 灰小字（参考来源）。

## 与其他两套的分工
- **晚点**（本套）：新闻/播客/访谈类的默认 —— 克制白描长段落
- **量子位**：需要强节奏、短平快的爆点新闻可选
- **深思圈**：观点文/组织文

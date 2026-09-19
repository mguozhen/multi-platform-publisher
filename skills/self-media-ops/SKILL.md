---
name: self-media-ops
description: Hunter「Hunter在跑」公众号与自媒体矩阵的完整运营流水线：X趋势/YouTube/播客/公众号文章选题 → 事实交叉核对 → 三套实测排版（晚点/量子位/深思圈）写作渲染 → deslop 机检 → 配图与封面生成 → 一键推公众号草稿箱。触发词：写一篇文章、写公众号、X trending 链接、用XX排版写、推草稿箱、自媒体发布。
---

# 自媒体运营 Skill（Hunter 在跑）

## 铁律（违反任何一条=返工）
1. **只进草稿箱，绝不群发**。发布=push 到 draft box，群发永远由 Hunter 手动。
2. **标题用「事实钩子式直陈」**：仍是新闻直陈句、仍禁悬念/对比/转折，但要把这篇最猛的事实或数字放进标题（「三个人，一个月，100 万美元 ARR」式）。基于某篇文章/视频写作时，标题逐字用原文标题。
3. **deslop 机检必须通过**（scripts/deslop_check.py）。高频踩雷：破折号——≤5 处；黑名单词：闭环、对齐、打法、解锁、体感、中文圈（注意"封闭环境"含"闭环"的子串误报，重写绕开）。
4. **文末必有两节**：「参考来源」（分级标注：官方原文 / 三方报道交叉 / X 单一来源 / 未核实，如实写"未看完整节目""未核对仓库"）＋「利益相关」（AI 客服按结果计费 + LLM 网关 Flatkey，与主题相关就写）。
5. **每张图发前必须 Read 目检**。配图语言随正文语言（中文文章配中文图），figs/ 按 zh|en|ja 分目录。
6. **文末关注钩子**：渲染器已自动加「关注 Agent101」行（主号 2026-09 定为 Agent101），不要删。
7. **对自己不利的事实照写**（BlockRun 体）：自家产品的短板、实测失败、来源拿不到，都如实交代，这是信用资产。

## 排版分工（三套复刻器，全部实测参数）
| 场景 | 排版 | 渲染器 | Playbook |
|---|---|---|---|
| **新闻/发布/融资（默认）** | 晚点 LatePost：黄荧光系统，金句前置，克制白描长段落 | scripts/build_wechat_latepost.py | playbooks/wechat-latepost-playbook.md |
| 强节奏爆点新闻（指定时用） | 量子位：绿色系统，短段落钩子，一键三连尾块 | scripts/build_wechat_qbit.py | playbooks/wechat-qbit-playbook.md |
| 观点文/组织文 | 深思圈：Optima 字体，编号小节，零装饰 | scripts/build_wechat_sisiquan.py | 参数注释在脚本头部 |

Markdown 约定（晚点）：`%% `导语｜`==x==`黄底引语｜`> `引用块｜`## `黄底居中H2｜图片下一行`*…*`=分析型图注｜`---`后=灰色小字来源。
量子位：`**x**`=绿色加粗结论句｜`## `=绿左条H2｜图注用`*…*`。

## 标准流水线（一篇文章 ≈ 30-50 分钟）
1. **选题输入**
   - X trend：`curl -A "<iPhone UA>" https://x.com/i/trending/<id>`，og:title/og:description 直接给出主题；trend id 是 snowflake，`(id>>22)+1288834974657` 得毫秒时间戳。
   - X 搜索素材：OAuth1 签名调 `/2/tweets/search/recent`（密钥 `~/.secrets/x.env`，注意 `set -a && source` 才能导出）。
   - YouTube/播客：yt-dlp 或 curl 下 mp3 → `~/Library/Python/3.9/bin/mlx_whisper <f> --model mlx-community/whisper-large-v3-turbo`（80 分钟音频约 8-10 分钟）。
   - 公众号文章：curl + iPhone UA 可拿全文；正文在 `id="js_content"`。
   - 播客雷达：`~/content-radar/radar.py --days 7 --min 45`。
2. **事实核对**：官方原文优先（WebFetch），三方报道交叉（Engadget/The Register/LawSites 这类），引语必须在转写稿里 grep 到原句才算核实。厂商口径一律标注"自家数字，无第三方复测"。
3. **写作**：新建 `~/<slug>-<style>/`（article.md + figs/zh/）。写完跑 deslop，改到过。
4. **配图**：新闻用**真实截图**（headless Chrome `--screenshot` 官方公告页/报道页，sips 转 1080 jpeg）；观点文用单线编辑插画（gpt-image-2 走 `router.flatkey.ai/v1/images/generations`，key=`~/.secrets/flatkey-cc.env` 的 FLATKEY_CC_KEY；基础 prompt 见 references/editorial-line-prompt.txt；挂了换 gemini-3-pro-image 走 chat）。
5. **封面**：`scripts/build_cover_songti.py --kicker "硅谷前沿 AI 观察 · Hunter 在跑" --title "<标题>" --bg <线稿底图> --layout band`（底图=单线画、内容压在下三分之一的横构图）。封面文案必须与最终标题一致。
6. **推草稿**：改 scripts/push_to_wechat.template.py 顶部 TITLE/DIGEST（≤120字）→ `set -a && source ~/.secrets/wechat.env && set +a && python3 push_to_wechat.py`。需要换封面重推时：先推新草稿，再 `draft/delete` 旧 media_id。
7. **交付**：`open` 封面给 Hunter；汇报只说结论+骨架；提醒"只进草稿箱"。

## 全平台（仅 Hunter 说「全平台」时）
文本→音频→视频三阶段。X=hunterguo101 Premium 单条英文长文（绝不发 thread），X Article 无 API 只能手贴；LinkedIn 英文+配图（em-dash 会被 slop 门拦）；Bluesky/Mastodon 先起 Tailscale 出口 mini1；发布器 `~/self-media/tools/allplatform.py`。

## 依赖的密钥（只列名字，值在本机）
`~/.secrets/wechat.env`（WECHAT_APPID/SECRET）· `~/.secrets/x.env`（X_API_KEY/SECRET, X_ACCESS_TOKEN/SECRET）· `~/.secrets/flatkey-cc.env`（FLATKEY_CC_KEY）

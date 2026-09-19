#!/usr/bin/env python3
"""AI 味体检。跑一遍 article.md，把机器能抓的毛病全列出来。

用法：
    python3 deslop_check.py article.md
    python3 deslop_check.py article.md --dash-limit 8   # 作者本人爱用破折号就放宽

退出码：0 全过；2 有一票否决项没过。
"""
import argparse, re, sys, pathlib

HARD = [                                    # (名字, 正则, 上限, 说明)
    ("破折号",     r"——",                                    5,
     "最强的 AI 指纹。先去看这个号已发的文章，按作者本人习惯定阈值"),
    ("自我铺垫",   r"顺手说清|先说清楚|说白了|说得再直白|这里补充一下|简单来说",  0,
     "说话之前先宣布自己要说话，人不这么讲"),
    ("圈内黑话",   r"中文圈|体感|对齐|解锁|赋能|抓手|颗粒度|心智|打法|闭环|垂类|生态位", 0,
     "圈外人不这么说话，40 岁读者会出戏"),
    ("关键词堆砌", r"^关键词[：:]",                            0,
     "SEO 垃圾的标志，正文自然出现就够了"),
    ("空泛夸张",   r"颠覆|革命|炸裂|史诗级|封神|遥遥领先",      2,
     "堆形容词代替讲事实"),
]

SOFT = [
    ("「真正」",   r"真正",        3, "靠副词强调，而不是靠事实强调"),
    ("三段排比",   r"不仅.{0,20}而且.{0,20}更",  0, "AI 最爱的句式，两项优于三项"),
    ("升华结尾",   r"让我们|拥抱变化|时代的浪潮|未来已来", 0, "鸡汤收尾"),
]


def check(path, dash_limit, allow=()):
    text = pathlib.Path(path).read_text(encoding="utf-8")
    body = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    cn = len(re.findall(r"[一-鿿]", body))

    print(f"\n{path}  中文 {cn} 字\n")
    failed = False

    print("【一票否决项】")
    for name, pat, limit, why in HARD:
        if name == "破折号":
            limit = dash_limit
        hits = [h for h in re.findall(pat, body, re.M) if h not in allow]
        ok = len(hits) <= limit
        mark = "✓" if ok else "✗"
        print(f"  {mark} {name:<10} {len(hits):>3} 处 (上限 {limit})")
        if not ok:
            failed = True
            print(f"      {why}")
            for m in list(dict.fromkeys(hits))[:6]:
                for mm in re.finditer(re.escape(m), body):
                    ctx = body[max(0, mm.start()-28):mm.start()+28].replace("\n", " ")
                    print(f"      …{ctx}…")
                    break

    print("\n【需要自己判断的】")
    for name, pat, limit, why in SOFT:
        hits = re.findall(pat, body)
        mark = "·" if len(hits) <= limit else "!"
        print(f"  {mark} {name:<10} {len(hits):>3} 处 (建议 ≤{limit})  {why if len(hits) > limit else ''}")

    paras = [p for p in body.split("\n\n")
             if p.strip() and not p.strip().startswith(("#", ">", "-", "!"))]
    lens = [len(re.findall(r"[一-鿿]", p)) for p in paras]
    if lens:
        avg = sum(lens) / len(lens)
        spread = max(lens) - min(lens)
        print(f"\n【节奏】段落 {len(lens)} 个，平均 {avg:.0f} 字，最长 {max(lens)}，最短 {min(lens)}")
        if spread < 40:
            print("  ! 段落长度太均匀，读起来像机器。真人写作长短交错，会有单句成段")

    quotes = len(re.findall(r"^> \*\*", body, re.M))
    heads = len(re.findall(r"^## ", body, re.M))
    if heads and quotes > heads:
        print(f"  ! 金句 {quotes} 句 / 小节 {heads} 个 —— 满篇金句等于满篇没重点")

    print("\n" + ("✗ 有一票否决项没过，改完再跑一遍\n" if failed else "✓ 机检通过\n"))
    return 2 if failed else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--dash-limit", type=int, default=5)
    ap.add_argument("--allow", default="",
                    help="逗号分隔的豁免词。有些词在特定选题里是主题术语不是黑话，"
                         "比如写 loop 分工的文章里「闭环」就是主题词。例：--allow 闭环,生态")
    a = ap.parse_args()
    allow = tuple(x.strip() for x in a.allow.split(",") if x.strip())
    sys.exit(check(a.file, a.dash_limit, allow))

"""dry-adapt — 只跑 Claude 改写，不发布。验证 service 端到端 + 看每个平台的产出。

用法:
  python3 -m mpp.dry_adapt <article-path> [--platforms p1,p2,...] [--out <dir>]
"""
from __future__ import annotations
import argparse, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from claude_call import claude_adapt  # noqa: E402

PLAYBOOKS = Path.home() / "self-media" / "playbooks"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("article")
    ap.add_argument("--platforms", default="linkedin,devto")
    ap.add_argument("--out", default="/tmp/mpp-dry")
    ap.add_argument("--model", default="sonnet")
    args = ap.parse_args()

    article = Path(args.article).expanduser().read_text(encoding="utf-8")
    outdir = Path(args.out); outdir.mkdir(parents=True, exist_ok=True)

    for plat in [p.strip() for p in args.platforms.split(",") if p.strip()]:
        pb = (PLAYBOOKS / f"{plat}.md").read_text(encoding="utf-8")
        t0 = time.time()
        print(f"[{plat}] adapting...", file=sys.stderr, flush=True)
        try:
            out = claude_adapt(article=article, playbook=pb,
                               platform=plat, model=args.model)
        except Exception as e:
            print(f"[{plat}] FAILED: {e}", file=sys.stderr)
            continue
        dt = time.time() - t0
        path = outdir / f"{plat}.md"
        path.write_text(out, encoding="utf-8")
        print(f"[{plat}] {len(out)} chars in {dt:.1f}s → {path}", file=sys.stderr)


if __name__ == "__main__":
    main()

"""
视频生成 — flatkey 视频 API (router.flatkey.ai，异步任务)。

  submit(prompt, model, metadata)        -> task_id
  status(task_id)                        -> data dict (status/progress/result_url)
  generate_video(prompt, out_path, ...)  -> Path   (submit + 轮询 + 下载，阻塞)

模型: video-fast (60-120s, 草稿/预览) / video-pro (120-300s, 正式)
异步: 创建任务 → 轮询 SUCCESS → 带 token 下载 result_url。

ENV (telegram-bridge/.env):
  FLATKEY_VIDEO_API_KEY    seedance 分组的视频 key
  FLATKEY_VIDEO_BASE_URL   默认 https://router.flatkey.ai

CLI (会真提交、计费):
  python3 video_gen.py "一杯冒热气的咖啡，镜头推近" out.mp4 [video-fast|video-pro]
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) selfmedia-bridge"


# ─────────────────── env ─────────────────────────
def _load_env() -> tuple[str, str]:
    env_file = Path(__file__).resolve().parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    key = os.environ.get("FLATKEY_VIDEO_API_KEY", "")
    base = os.environ.get("FLATKEY_VIDEO_BASE_URL", "https://router.flatkey.ai")
    if not key:
        raise RuntimeError("缺少 FLATKEY_VIDEO_API_KEY (写进 .env)")
    return key, base.rstrip("/")


# ─────────────────── HTTP ─────────────────────────
def _req(method: str, url: str, key: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Authorization": f"Bearer {key}", "User-Agent": UA}
    if data:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:300]
        raise RuntimeError(f"HTTP {e.code}: {body}") from e


# ─────────────────── public API ─────────────────────────
def submit(prompt: str, model: str = "video-fast",
           metadata: dict | None = None) -> str:
    """创建视频任务，返回 task_id。"""
    key, base = _load_env()
    body: dict = {"model": model, "prompt": prompt}
    if metadata:
        body["metadata"] = metadata
    resp = _req("POST", f"{base}/v1/video/generations", key, body)
    tid = resp.get("task_id") or resp.get("id")
    if not tid:
        raise RuntimeError(f"提交未返回 task_id: {resp}")
    return tid


def status(task_id: str) -> dict:
    """查询任务状态，返回 data 块 (status/progress/result_url/fail_reason)。"""
    key, base = _load_env()
    resp = _req("GET", f"{base}/v1/video/generations/{task_id}", key)
    return resp.get("data", resp)


def download(task_id: str, out_path) -> Path:
    """下载已完成任务的视频 (result_url 需带 token)。"""
    key, base = _load_env()
    out = Path(out_path).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    url = f"{base}/v1/videos/{task_id}/content"
    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {key}", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=180) as r:
        out.write_bytes(r.read())
    return out


def generate_video(prompt: str, out_path, model: str = "video-fast",
                   metadata: dict | None = None, poll_interval: int = 8,
                   timeout: int = 600, on_progress=None) -> Path:
    """submit → 轮询 → 下载，阻塞直到完成。失败抛 RuntimeError。"""
    tid = submit(prompt, model, metadata)
    deadline = time.time() + timeout
    while time.time() < deadline:
        d = status(tid)
        st = (d.get("status") or "").upper()
        if on_progress:
            on_progress(st, d.get("progress", ""))
        if st == "SUCCESS":
            return download(tid, out_path)
        if st == "FAILURE":
            raise RuntimeError(f"视频生成失败: {d.get('fail_reason', 'unknown')}")
        time.sleep(poll_interval)
    raise RuntimeError(f"视频生成超时 ({timeout}s)，task_id={tid}")


# ─────────────────── cli ─────────────────────────
def main() -> None:
    args = sys.argv[1:]
    if len(args) < 2:
        print('用法: python3 video_gen.py "prompt" out.mp4 [video-fast|video-pro]')
        print("⚠️  会真提交任务并计费")
        sys.exit(1)
    model = args[2] if len(args) > 2 else "video-fast"
    print(f"提交中… model={model}")
    try:
        p = generate_video(
            args[0], args[1], model=model,
            on_progress=lambda s, pr: print(f"  status={s} progress={pr}"))
        print(f"✅ 视频已生成 → {p} ({p.stat().st_size} bytes)")
    except RuntimeError as e:
        sys.exit(f"❌ {e}")


if __name__ == "__main__":
    main()

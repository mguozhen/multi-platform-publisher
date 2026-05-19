#!/usr/bin/env python3
"""
Hacker News 发布器 — 浏览器自动化（HN 无提交 API，submit 表单是纯 HTML）。

半自动:打开持久 profile 的 Chrome → 等你登录 HN → 打开 submit 页
→ 填 title + url（链接帖）或 text（文本帖）→ --auto-publish 则自动点 submit。

用法:
  python3 hn_publish.py --title "..." --url "https://..."        # 链接帖
  python3 hn_publish.py --title "..." --text-file post.md        # 文本帖
  加 --auto-publish 自动提交。

⚠️ HN 反 self-promo 极严。一次只发一个真的够硬的东西，绝不进例行全平台扫。
   带营销味的提交会被 flag 到 dead、账号会被 shadowban。

登录态存进 ~/self-media/.chrome-hn-profile。
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

PROFILE_DIR = Path("/Users/hunter/self-media/.chrome-hn-profile")
SHOT_DIR = Path("/Users/hunter/self-media/content/hn")


def make_driver(headless: bool = False) -> Chrome:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    opts = Options()
    opts.add_argument(f"--user-data-dir={PROFILE_DIR}")
    opts.add_argument("--window-size=1300,1000")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    if headless:
        opts.add_argument("--headless=new")
    return webdriver.Chrome(options=opts)


def wait_for_login(driver: Chrome, timeout: int) -> None:
    print("Opening news.ycombinator.com...", flush=True)
    driver.get("https://news.ycombinator.com/")
    deadline = time.time() + timeout
    while time.time() < deadline:
        # 已登录:右上角有 logout 链接
        logged = bool(driver.find_elements(By.ID, "logout")) or bool(
            driver.find_elements(By.XPATH, "//a[contains(@href,'logout')]"))
        print(f"Login check: logged_in={logged}", flush=True)
        if logged:
            print("HN login appears ready.", flush=True)
            return
        print("Waiting for HN login (请在窗口里登录 Hacker News)...", flush=True)
        time.sleep(5)
    raise TimeoutException("Timed out waiting for HN login.")


def submit(driver: Chrome, title: str, url: str, text: str,
           auto: bool) -> None:
    print("Opening HN submit page...", flush=True)
    driver.get("https://news.ycombinator.com/submit")
    time.sleep(3)
    # HN submit 表单:input[name=title] / input[name=url] / textarea[name=text]
    t = driver.find_elements(By.CSS_SELECTOR, "input[name='title']")
    if not t:
        SHOT_DIR.mkdir(parents=True, exist_ok=True)
        driver.save_screenshot(str(SHOT_DIR / "hn-submit-failed.png"))
        raise TimeoutException(
            "HN submit form not found (可能没登录)。截图 content/hn/")
    t[0].clear()
    t[0].send_keys(title)
    print("Filled title.", flush=True)
    if url:
        u = driver.find_elements(By.CSS_SELECTOR, "input[name='url']")
        if u:
            u[0].clear()
            u[0].send_keys(url)
            print("Filled url (link post).", flush=True)
    elif text:
        tx = driver.find_elements(By.CSS_SELECTOR, "textarea[name='text']")
        if tx:
            tx[0].clear()
            tx[0].send_keys(text)
            print("Filled text (text post).", flush=True)
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    driver.save_screenshot(str(SHOT_DIR / "hn-submit-filled.png"))
    if auto:
        btns = driver.find_elements(By.CSS_SELECTOR, "input[type='submit']")
        if btns:
            btns[0].click()
            print("Clicked submit.", flush=True)
            time.sleep(5)
    else:
        print("Draft filled. Review and click submit manually.", flush=True)


def watch_and_open(driver: Chrome, timeout: int = 900) -> str | None:
    """提交后 HN 跳到 /newest 或帖子页;抓 item 链接。"""
    print("Watching for submit...", flush=True)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            url = driver.current_url
        except Exception:  # noqa: BLE001
            return None
        if "item?id=" in url or url.rstrip("/").endswith("/newest"):
            print(f"PUBLISHED_URL: {url}", flush=True)
            try:
                subprocess.run(["open", url], check=False)
            except Exception:  # noqa: BLE001
                pass
            return url
        time.sleep(3)
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Hacker News 半自动发布")
    parser.add_argument("--title", required=True)
    parser.add_argument("--url", default="")
    parser.add_argument("--text-file", default="")
    parser.add_argument("--auto-publish", action="store_true")
    parser.add_argument("--login-timeout", type=int, default=600)
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    if len(args.title) > 80:
        raise SystemExit("HN 标题上限 80 字符。")
    text = ""
    if args.text_file:
        text = Path(args.text_file).expanduser().read_text(encoding="utf-8")
    if not args.url and not text:
        raise SystemExit("需要 --url（链接帖）或 --text-file（文本帖）。")

    driver = make_driver(headless=args.headless)
    try:
        print(f"Using Chrome profile: {PROFILE_DIR}", flush=True)
        wait_for_login(driver, args.login_timeout)
        submit(driver, args.title, args.url, text, args.auto_publish)
        watch_and_open(driver)
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("Stopped by user.")
    except Exception as exc:  # noqa: BLE001
        print(f"Automation stopped: {exc}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()

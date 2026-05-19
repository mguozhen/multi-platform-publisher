#!/usr/bin/env python3
"""
Reddit 发布器 — 浏览器自动化（按 Hunter 指定，不走官方 API）。

半自动:打开持久 profile 的 Chrome → 等你登录 Reddit → 打开 submit 页
→ 选 subreddit → 填标题 + 正文 → 你审核后手动点 Post。

用法:
  python3 reddit_publish.py <article_dir> --subreddit <名字，不带 r/>
  article_dir 里要有 post.md（正文）+ meta.md（## Primary Title）

⚠️ Reddit 反 self-promo 极严。每个 subreddit 规则不同，直发广告会被秒删/封号。
   内容走「真实分享 / 复盘 / 提问」口吻，不要标题党，发布频率要克制。

登录态存进 ~/self-media/.chrome-reddit-profile，之后不用再登。
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
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from substack_publish_helper import read_title

PROFILE_DIR = Path("/Users/hunter/self-media/.chrome-reddit-profile")
SHOT_DIR = Path("/Users/hunter/self-media/content/reddit")


def load_article(article_dir: Path) -> dict[str, str]:
    post = (article_dir / "post.md").read_text(encoding="utf-8")
    meta = (article_dir / "meta.md").read_text(encoding="utf-8")
    return {"title": read_title(meta), "post": post}


def make_driver(headless: bool = False) -> Chrome:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    opts = Options()
    opts.add_argument(f"--user-data-dir={PROFILE_DIR}")
    opts.add_argument("--window-size=1400,1000")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    if headless:
        opts.add_argument("--headless=new")
    return webdriver.Chrome(options=opts)


def wait_for_login(driver: Chrome, timeout: int) -> None:
    print("Opening reddit.com...", flush=True)
    driver.get("https://www.reddit.com/")
    deadline = time.time() + timeout
    while time.time() < deadline:
        body = driver.find_element(By.TAG_NAME, "body").text
        # 未登录信号
        not_logged = ("Log In" in body and "Sign Up" in body
                      and "Create Post" not in body)
        print(f"Login check: logged_in={not not_logged}", flush=True)
        if not not_logged:
            print("Reddit login appears ready.", flush=True)
            return
        print("Waiting for Reddit login in browser window "
              "(请在窗口里登录 Reddit)...", flush=True)
        time.sleep(5)
    raise TimeoutException("Timed out waiting for Reddit login.")


def open_submit(driver: Chrome, subreddit: str) -> None:
    url = f"https://www.reddit.com/r/{subreddit}/submit/?type=TEXT"
    print(f"Opening submit page: {url}", flush=True)
    driver.get(url)
    time.sleep(6)
    body = driver.find_element(By.TAG_NAME, "body").text
    if "Title" in body or "Body" in body or "Post" in body:
        print("Reddit submit page appears open.", flush=True)
        return
    # 兜底:通用 submit 页
    driver.get("https://www.reddit.com/submit?type=TEXT")
    time.sleep(6)


def _fill_field(driver: Chrome, selectors: list[str], text: str,
                label: str) -> bool:
    """尝试多个 selector（含 shadow DOM faceplate 控件）填入文本。"""
    for sel in selectors:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
        except Exception:  # noqa: BLE001
            continue
        for el in els:
            try:
                el.click()
                el.send_keys(text)
                print(f"Filled {label} via: {sel}", flush=True)
                return True
            except Exception:  # noqa: BLE001
                continue
    # JS 兜底:写进第一个匹配的 input/textarea/contenteditable
    return False


def fill_post(driver: Chrome, article: dict[str, str]) -> None:
    print("Filling Reddit post...", flush=True)
    # Reddit 新版 submit 用 <faceplate-*> / shadow DOM。标题常是 textarea[name=title]
    title_ok = _fill_field(
        driver,
        ["textarea[name='title']", "textarea[placeholder*='Title']",
         "input[name='title']", "[contenteditable='true'][aria-label*='Title']"],
        article["title"], "title")
    # 正文:多为 contenteditable 富文本
    body_ok = _fill_field(
        driver,
        ["[contenteditable='true'][aria-label*='ody']",
         "div[contenteditable='true']",
         "textarea[name='body']", "textarea[placeholder*='Text']"],
        article["post"], "body")
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    driver.save_screenshot(str(SHOT_DIR / "reddit-draft-filled.png"))
    print(f"Screenshot: content/reddit/reddit-draft-filled.png "
          f"(title_ok={title_ok}, body_ok={body_ok})", flush=True)
    if not (title_ok and body_ok):
        print("⚠️ 部分字段没填上 — 看截图,Reddit submit 是 shadow DOM,"
              "可能要按截图调 selector。", flush=True)


def watch_and_open(driver: Chrome, timeout: int = 1800) -> str | None:
    """监测你点 Post 后跳转到的已发布帖子 URL → 打印 + 自动 open。"""
    print("Watching for publish (点 Post 后自动抓链接)...", flush=True)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            url = driver.current_url
        except Exception:  # noqa: BLE001
            return None
        if "/comments/" in url:
            print(f"PUBLISHED_URL: {url}", flush=True)
            try:
                subprocess.run(["open", url], check=False)
            except Exception:  # noqa: BLE001
                pass
            return url
        time.sleep(4)
    print("Publish not detected within timeout.", flush=True)
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Reddit 半自动发布（浏览器自动化）")
    parser.add_argument("article_dir", type=Path)
    parser.add_argument("--subreddit", required=True,
                        help="目标 subreddit，不带 r/")
    parser.add_argument("--login-timeout", type=int, default=600)
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    article = load_article(args.article_dir.resolve())
    if not article["title"] or not article["post"].strip():
        raise SystemExit("Article package missing title or post body.")

    driver = make_driver(headless=args.headless)
    try:
        print(f"Using Chrome profile: {PROFILE_DIR}", flush=True)
        wait_for_login(driver, args.login_timeout)
        open_submit(driver, args.subreddit)
        fill_post(driver, article)
        print(f"Draft filled in r/{args.subreddit}. "
              f"Review the browser window and Post manually.")
        print(f"Title: {article['title']}")
        watch_and_open(driver)
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("Stopped by user.")
    except Exception as exc:  # noqa: BLE001
        print(f"Automation stopped: {exc}", file=sys.stderr)
        try:
            print(f"Current URL: {driver.current_url}", file=sys.stderr)
        except Exception:  # noqa: BLE001
            pass
        raise


if __name__ == "__main__":
    main()

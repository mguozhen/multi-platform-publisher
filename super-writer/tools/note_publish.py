#!/usr/bin/env python3
"""
note.com 发布器 — 浏览器自动化（note 无开放 API）。

半自动:打开持久 profile 的 Chrome → 等你登录 note → 自动开「テキスト」编辑器
→ 自动填标题 + 正文 → 你审核后手动点「公開」。

用法:
  python3 note_publish.py <article_dir>
  article_dir 里要有 post.md（正文）+ meta.md（## Primary Title / ## Tags）

登录态存进 ~/self-media/.chrome-note-profile，之后不用再登。
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

from substack_publish_helper import read_section, read_title

PROFILE_DIR = Path("/Users/hunter/self-media/.chrome-note-profile")
SHOT_DIR = Path("/Users/hunter/self-media/content/note")


def load_article(article_dir: Path) -> dict[str, str]:
    post = (article_dir / "post.md").read_text(encoding="utf-8")
    meta = (article_dir / "meta.md").read_text(encoding="utf-8")
    return {
        "title": read_title(meta),
        "tags": read_section(meta, "Tags"),
        "post": post,
    }


def make_driver(headless: bool = False) -> Chrome:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    opts = Options()
    opts.add_argument(f"--user-data-dir={PROFILE_DIR}")
    opts.add_argument("--window-size=1400,1000")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    if headless:
        opts.add_argument("--headless=new")
    return webdriver.Chrome(options=opts)


def xpath_literal(text: str) -> str:
    if "'" not in text:
        return f"'{text}'"
    if '"' not in text:
        return f'"{text}"'
    parts = text.split("'")
    return "concat(" + ", \"'\", ".join(f"'{p}'" for p in parts) + ")"


def click_text(driver: Chrome, texts: list[str], timeout: int = 8) -> bool:
    wait = WebDriverWait(driver, timeout)
    for text in texts:
        for xpath in (
            f"//button[contains(normalize-space(.), {xpath_literal(text)})]",
            f"//a[contains(normalize-space(.), {xpath_literal(text)})]",
            f"//*[self::div or self::span][contains(normalize-space(.), "
            f"{xpath_literal(text)})]",
        ):
            try:
                el = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
                el.click()
                return True
            except Exception:  # noqa: BLE001
                continue
    return False


def wait_for_login(driver: Chrome, timeout: int) -> None:
    print("Opening note.com...", flush=True)
    driver.get("https://note.com/")
    deadline = time.time() + timeout
    while time.time() < deadline:
        url = driver.current_url
        body = driver.find_element(By.TAG_NAME, "body").text
        # 未登录信号:注册/登录页
        not_logged = any(s in body for s in (
            "noteにようこそ", "会員登録", "Googleで登録", "Appleで登録",
            "メールで登録"))
        print(f"Login check: {url} | logged_in={not not_logged}", flush=True)
        if not not_logged and ("投稿" in body or "おすすめ" in body
                               or "フォロー中" in body or "タイムライン" in body):
            print("note login appears ready.", flush=True)
            return
        print("Waiting for note login in browser window "
              "(请在窗口里登录 note)...", flush=True)
        time.sleep(5)
    raise TimeoutException("Timed out waiting for note login.")


def open_new_text_note(driver: Chrome) -> None:
    # 直链优先
    for url in ("https://note.com/notes/new", "https://editor.note.com/new"):
        print(f"Trying editor route: {url}", flush=True)
        driver.get(url)
        time.sleep(4)
        body = driver.find_element(By.TAG_NAME, "body").text
        if "記事タイトル" in body or "タイトル" in body or "公開に進む" in body:
            print("note editor appears open.", flush=True)
            return
    # 兜底:首页点「投稿」→「テキスト」
    driver.get("https://note.com/")
    time.sleep(3)
    if click_text(driver, ["投稿", "投稿する"], timeout=6):
        time.sleep(2)
        click_text(driver, ["テキスト", "記事"], timeout=6)
        time.sleep(4)
        body = driver.find_element(By.TAG_NAME, "body").text
        if "タイトル" in body or "公開に進む" in body:
            print("note editor open after 投稿→テキスト.", flush=True)
            return
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    driver.save_screenshot(str(SHOT_DIR / "note-open-editor-failed.png"))
    raise TimeoutException(
        "Could not open note text editor. Screenshot saved to content/note/")


def paste_into_active(driver: Chrome, text: str) -> None:
    driver.execute_script(
        """
        const text = arguments[0];
        const el = document.activeElement;
        if (!el) return;
        if (el.isContentEditable) {
          el.focus();
          document.execCommand('selectAll', false, null);
          document.execCommand('insertText', false, text);
        } else {
          el.value = text;
          el.dispatchEvent(new Event('input', { bubbles: true }));
          el.dispatchEvent(new Event('change', { bubbles: true }));
        }
        """,
        text,
    )


def fill_editor(driver: Chrome, article: dict[str, str]) -> None:
    print("Filling note editor...", flush=True)
    title_filled = False
    for selector in (
        "textarea[placeholder*='タイトル']",
        "input[placeholder*='タイトル']",
        "[contenteditable='true'][data-placeholder*='タイトル']",
        "[contenteditable='true'][aria-label*='タイトル']",
        "h1[contenteditable='true']",
    ):
        els = driver.find_elements(By.CSS_SELECTOR, selector)
        if els:
            els[0].click()
            time.sleep(0.4)
            # 真实键盘输入 —— React textarea 用 JS set value 不注册
            try:
                els[0].send_keys(article["title"])
            except Exception:  # noqa: BLE001
                paste_into_active(driver, article["title"])
            title_filled = True
            print(f"Filled title via: {selector} (send_keys)", flush=True)
            break
    if not title_filled:
        print("Title selector not found; tab fallback.", flush=True)
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.TAB)
        paste_into_active(driver, article["title"])

    time.sleep(0.6)
    # 正文:note 正文是 contenteditable，placeholder 含「書いて」
    body_filled = False
    for selector in (
        "[contenteditable='true'][data-placeholder*='書いて']",
        "div[contenteditable='true'][aria-label*='本文']",
        "div.ProseMirror[contenteditable='true']",
        "[contenteditable='true']",
    ):
        els = driver.find_elements(By.CSS_SELECTOR, selector)
        # 跳过标题那个 contenteditable
        for el in els:
            ph = (el.get_attribute("data-placeholder") or "")
            if "タイトル" in ph:
                continue
            el.click()
            paste_into_active(driver, article["post"])
            body_filled = True
            print(f"Filled body via: {selector}", flush=True)
            break
        if body_filled:
            break
    if not body_filled:
        print("Body selector not found; tab fallback.", flush=True)
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.TAB)
        paste_into_active(driver, article["post"])

    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    driver.save_screenshot(str(SHOT_DIR / "note-draft-filled.png"))
    print("Draft screenshot saved to content/note/note-draft-filled.png",
          flush=True)


def publish_now(driver: Chrome) -> bool:
    """自动走 note 发布流程:公開に進む → 投稿する。"""
    print("Auto-publishing: 点「公開に進む」...", flush=True)
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    if not click_text(driver, ["公開に進む", "公開設定"], timeout=14):
        driver.save_screenshot(str(SHOT_DIR / "note-publish-step1-failed.png"))
        print("⚠️ 找不到「公開に進む」(截图 note-publish-step1-failed.png)",
              flush=True)
        return False
    time.sleep(6)
    driver.save_screenshot(str(SHOT_DIR / "note-publish-settings.png"))
    # 发布设置页 → 最终发布按钮
    if click_text(driver, ["投稿する", "公開する", "今すぐ公開", "公開"],
                  timeout=14):
        print("Clicked final publish button.", flush=True)
        time.sleep(7)
        driver.save_screenshot(str(SHOT_DIR / "note-published.png"))
        return True
    driver.save_screenshot(str(SHOT_DIR / "note-publish-step2-failed.png"))
    print("⚠️ 找不到最终发布按钮(截图 note-publish-step2-failed.png)",
          flush=True)
    return False


def watch_and_open(driver: Chrome, timeout: int = 1800) -> str | None:
    """监测你点「公開」后跳转到的已发布 URL → 打印 + 自动 open。"""
    print("Watching for publish (点「公開に進む」→ 投稿する 后自动抓链接)...",
          flush=True)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            url = driver.current_url
        except Exception:  # noqa: BLE001
            return None
        if re.search(r"note\.com/[^/]+/n/n[0-9a-zA-Z]+", url) \
                and "/edit" not in url:
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
    parser = argparse.ArgumentParser(description="note.com 半自动发布")
    parser.add_argument("article_dir", type=Path)
    parser.add_argument("--login-timeout", type=int, default=240)
    parser.add_argument("--auto-publish", action="store_true",
                        help="自动点 公開に進む → 投稿する,不等人工")
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    article = load_article(args.article_dir.resolve())
    if not article["title"] or not article["post"].strip():
        raise SystemExit("Article package missing title or post body.")

    driver = make_driver(headless=args.headless)
    try:
        print(f"Using Chrome profile: {PROFILE_DIR}", flush=True)
        wait_for_login(driver, args.login_timeout)
        open_new_text_note(driver)
        fill_editor(driver, article)
        print(f"Title: {article['title']}")
        if args.auto_publish:
            publish_now(driver)
        else:
            print("Draft filled. Review and 公開 manually.")
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

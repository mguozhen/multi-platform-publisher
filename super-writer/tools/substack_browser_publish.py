#!/usr/bin/env python3
from __future__ import annotations

import argparse
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

from substack_publish_helper import read_section, read_tags, read_title


PROFILE_DIR = Path("/Users/hunter/self-media/.chrome-substack-profile")


def load_article(article_dir: Path) -> dict[str, str]:
    post = (article_dir / "post.md").read_text(encoding="utf-8")
    meta = (article_dir / "meta.md").read_text(encoding="utf-8")
    return {
        "title": read_title(meta),
        "subtitle": read_section(meta, "Subtitle"),
        "excerpt": read_section(meta, "Excerpt"),
        "tags": read_tags(meta),
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


def wait_for_login(driver: Chrome, timeout: int) -> None:
    print("Opening Substack home...", flush=True)
    driver.get("https://substack.com/home")
    deadline = time.time() + timeout
    while time.time() < deadline:
        url = driver.current_url
        body = driver.find_element(By.TAG_NAME, "body").text.lower()
        print(f"Login check: {url}", flush=True)
        if "dashboard" in url or "home" in url:
            if "sign in" not in body[:500] and "log in" not in body[:500]:
                print("Login appears ready.", flush=True)
                return
        if "new post" in body or "dashboard" in body or "notes" in body:
            print("Dashboard/home controls found.", flush=True)
            return
        print("Waiting for Substack login in browser window...")
        time.sleep(5)
    raise TimeoutException("Timed out waiting for Substack login.")


def click_text(driver: Chrome, texts: list[str], timeout: int = 8) -> bool:
    wait = WebDriverWait(driver, timeout)
    for text in texts:
        xpaths = [
            f"//button[contains(normalize-space(.), {xpath_literal(text)})]",
            f"//a[contains(normalize-space(.), {xpath_literal(text)})]",
            f"//*[self::div or self::span][contains(normalize-space(.), {xpath_literal(text)})]",
        ]
        for xpath in xpaths:
            try:
                el = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
                el.click()
                return True
            except Exception:
                continue
    return False


def xpath_literal(text: str) -> str:
    if "'" not in text:
        return f"'{text}'"
    if '"' not in text:
        return f'"{text}"'
    parts = text.split("'")
    return "concat(" + ", \"'\", ".join(f"'{part}'" for part in parts) + ")"


def open_new_post(driver: Chrome) -> None:
    candidates = [
        "https://substack.com/publish/post",
        "https://substack.com/home",
        "https://substack.com/",
    ]
    for url in candidates:
        print(f"Trying editor route: {url}", flush=True)
        driver.get(url)
        time.sleep(3)
        body = driver.find_element(By.TAG_NAME, "body").text
        print(f"Current URL after route: {driver.current_url}", flush=True)
        if "Title" in body and ("Publish" in body or "Draft" in body):
            print("Editor appears open.", flush=True)
            return
        if click_text(driver, ["New post", "Create new", "Create", "Write"], timeout=4):
            print("Clicked create/new post control.", flush=True)
            time.sleep(4)
            body = driver.find_element(By.TAG_NAME, "body").text
            if "Title" in body or "Tell your story" in body or "Write something" in body:
                print("Editor appears open after click.", flush=True)
                return
        if click_text(driver, ["Text post", "Post"], timeout=3):
            print("Clicked text post/post control.", flush=True)
            time.sleep(4)
            return
    driver.save_screenshot("/Users/hunter/self-media/content/substack/substack-open-new-post-failed.png")
    raise TimeoutException("Could not open Substack new post editor. Screenshot saved to content/substack/substack-open-new-post-failed.png")


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
    print("Filling editor...", flush=True)
    body = driver.find_element(By.TAG_NAME, "body")
    body.send_keys(Keys.ESCAPE)

    # Try common title fields.
    title_filled = False
    for selector in [
        "textarea[placeholder*='Title']",
        "input[placeholder*='Title']",
        "[contenteditable='true'][data-placeholder*='Title']",
        "[contenteditable='true'][aria-label*='Title']",
    ]:
        els = driver.find_elements(By.CSS_SELECTOR, selector)
        if els:
            els[0].click()
            paste_into_active(driver, article["title"])
            title_filled = True
            print(f"Filled title using selector: {selector}", flush=True)
            break

    if not title_filled:
        print("Title field selector not found; using tab fallback.", flush=True)
        body.send_keys(Keys.TAB)
        paste_into_active(driver, article["title"])

    time.sleep(0.5)
    body.send_keys(Keys.TAB)
    paste_into_active(driver, article["subtitle"])
    print("Filled subtitle via keyboard focus.", flush=True)

    time.sleep(0.5)
    body.send_keys(Keys.TAB)
    paste_into_active(driver, article["post"])
    print("Filled post body via keyboard focus.", flush=True)
    driver.save_screenshot("/Users/hunter/self-media/content/substack/substack-draft-filled.png")


def main() -> None:
    parser = argparse.ArgumentParser(description="Open Substack and fill a draft post from an article package.")
    parser.add_argument("article_dir", type=Path)
    parser.add_argument("--login-timeout", type=int, default=180)
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    article_dir = args.article_dir.resolve()
    article = load_article(article_dir)
    if not article["title"] or not article["post"].strip():
        raise SystemExit("Article package missing title or post body.")

    driver = make_driver(headless=args.headless)
    try:
        print(f"Using Chrome profile: {PROFILE_DIR}", flush=True)
        wait_for_login(driver, args.login_timeout)
        open_new_post(driver)
        fill_editor(driver, article)
        print("Draft filled. Review the browser window and publish manually.")
        print(f"Title: {article['title']}")
        print(f"Tags to add manually if needed: {article['tags']}")
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("Stopped by user.")
    except Exception as exc:
        print(f"Automation stopped: {exc}", file=sys.stderr)
        print(f"Current URL: {driver.current_url}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()

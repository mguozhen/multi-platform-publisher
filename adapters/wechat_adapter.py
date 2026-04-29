"""
WeChat Official Account Adapter (微信公众号)
=============================================
Creates article drafts via the WeChat Official Account Platform API.

Required environment variables
------------------------------
- ``WECHAT_APPID``      – Official Account App ID
- ``WECHAT_APPSECRET``  – Official Account App Secret

References
----------
- Access Token:  https://developers.weixin.qq.com/doc/offiaccount/Basic_Information/Get_access_token.html
- Draft API:     https://developers.weixin.qq.com/doc/offiaccount/Draft_Box/Add_draft.html
- Media Upload:  https://developers.weixin.qq.com/doc/offiaccount/Asset_Management/New_temporary_material.html
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any
import re

import requests

from .base_adapter import BaseAdapter


class WeChatAdapter(BaseAdapter):
    """Adapter for WeChat Official Account (微信公众号)."""

    DISPLAY_NAME = "WeChat Official Account (微信公众号)"
    AUTH_METHOD = "API Token"
    FEATURES = ["draft_creation", "image_upload", "html_article"]
    MAX_IMAGES = 10

    BASE_URL = "https://api.weixin.qq.com/cgi-bin"

    def __init__(self, config: dict | None = None):
        super().__init__(config or {})
        self.appid = self.config.get("appid") or os.environ.get("WECHAT_APPID", "")
        self.appsecret = self.config.get("appsecret") or os.environ.get("WECHAT_APPSECRET", "")

        if not self.appid or not self.appsecret:
            raise ValueError(
                "WeChat credentials incomplete. Set WECHAT_APPID and WECHAT_APPSECRET."
            )

        self._access_token: str = ""
        self._token_expires: float = 0.0

    # ------------------------------------------------------------------
    # Access-token management
    # ------------------------------------------------------------------
    def _get_access_token(self) -> str:
        """Obtain or refresh the access token."""
        if self._access_token and time.time() < self._token_expires:
            return self._access_token

        resp = requests.get(
            f"{self.BASE_URL}/token",
            params={
                "grant_type": "client_credential",
                "appid": self.appid,
                "secret": self.appsecret,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        if "access_token" not in data:
            raise RuntimeError(
                f"WeChat token error: {data.get('errcode')} – {data.get('errmsg')}"
            )

        self._access_token = data["access_token"]
        # Token is valid for 7200 s; refresh 5 min early.
        self._token_expires = time.time() + data.get("expires_in", 7200) - 300
        return self._access_token

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------
    def publish(self, content: Any, images: list[str] | None = None) -> dict:
        """Create a draft article on the WeChat Official Account.

        *content* is expected to be a ``dict`` with keys:
        - ``title``   – article title
        - ``content`` – HTML body
        - ``digest``  – (optional) short summary
        - ``author``  – (optional) author name

        If *content* is a plain ``str``, it is wrapped automatically.
        """
        token = self._get_access_token()

        # Normalise content
        if isinstance(content, str):
            content = {"title": "Untitled", "content": content}

        # Upload a cover image if provided
        thumb_media_id = ""
        if images:
            thumb_media_id = self.upload_image(images[0]) or ""

        body_html = self._prepare_body_images(content.get("content", ""))

        article = {
            "title": content.get("title", "Untitled"),
            "author": content.get("author", ""),
            "digest": content.get("digest", ""),
            "content": body_html,
            "content_source_url": content.get("source_url", ""),
            "need_open_comment": 0,
            "only_fans_can_comment": 0,
        }
        if thumb_media_id:
            article["thumb_media_id"] = thumb_media_id

        payload = {"articles": [article]}

        resp = requests.post(
            f"{self.BASE_URL}/draft/add",
            params={"access_token": token},
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
            timeout=60,
        )

        data = resp.json()
        if data.get("errcode", 0) == 0:
            media_id = data.get("media_id", "")
            return {
                "success": True,
                "message": "WeChat draft created successfully.",
                "media_id": media_id,
                "url": None,  # Drafts have no public URL until published
            }
        return {
            "success": False,
            "error": f"WeChat API error {data.get('errcode')}: {data.get('errmsg')}",
        }

    def validate(self) -> bool:
        try:
            self._get_access_token()
            return True
        except Exception:
            return False

    def upload_image(self, image_path: str) -> str | None:
        """Upload a permanent *thumb* material and return its ``media_id``.

        WeChat draft articles require ``thumb_media_id`` from the permanent
        material API, not the temporary ``/media/upload`` image endpoint.
        """
        path = Path(image_path)
        if not path.exists():
            return None

        token = self._get_access_token()
        content_type = "image/jpeg"
        suffix = path.suffix.lower()
        if suffix == ".png":
            content_type = "image/png"
        elif suffix == ".gif":
            content_type = "image/gif"
        elif suffix == ".webp":
            content_type = "image/webp"

        with open(path, "rb") as f:
            resp = requests.post(
                f"{self.BASE_URL}/material/add_material",
                params={"access_token": token, "type": "thumb"},
                files={"media": (path.name, f, content_type)},
                timeout=120,
            )

        data = resp.json()
        if "media_id" in data:
            return data["media_id"]
        return None

    # ------------------------------------------------------------------
    # Extended helpers
    # ------------------------------------------------------------------
    def _prepare_body_images(self, html: str) -> str:
        """Upload local inline images to WeChat CDN and replace src URLs."""
        if not html:
            return html

        def repl(match: re.Match) -> str:
            src = match.group(1)
            if src.startswith("http://mmbiz.qpic.cn") or src.startswith("https://mmbiz.qpic.cn"):
                return match.group(0)
            if src.startswith("http://") or src.startswith("https://"):
                return match.group(0)
            uploaded = self.upload_permanent_image(src)
            if not uploaded:
                raise RuntimeError(f"WeChat body image upload failed for: {src}")
            return match.group(0).replace(src, uploaded)

        return re.sub(r'<img[^>]+src="([^"]+)"', repl, html)

    def upload_permanent_image(self, image_path: str) -> str | None:
        """Upload a *permanent* image material (for article body ``<img>`` tags).

        Returns the image URL on WeChat CDN.
        """
        path = Path(image_path)
        if not path.exists():
            return None

        token = self._get_access_token()

        with open(path, "rb") as f:
            resp = requests.post(
                f"{self.BASE_URL}/media/uploadimg",
                params={"access_token": token},
                files={"media": (path.name, f, "image/jpeg")},
                timeout=120,
            )

        data = resp.json()
        return data.get("url")

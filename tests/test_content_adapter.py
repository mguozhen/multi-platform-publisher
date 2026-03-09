"""
Tests for ContentAdapter
========================
Run with:  python3 -m pytest tests/ -v
"""

import sys
from pathlib import Path

# Ensure the skill root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.content_adapter import ContentAdapter


adapter = ContentAdapter()


# ------------------------------------------------------------------
# Twitter
# ------------------------------------------------------------------
class TestTwitterAdaptation:
    def test_short_tweet(self):
        result = adapter.adapt("Hello world!", "twitter")
        assert isinstance(result, str)
        assert len(result) <= 280

    def test_long_content_becomes_thread(self):
        long_text = "This is a sentence. " * 50
        result = adapter.adapt(long_text, "twitter", as_thread=True)
        assert isinstance(result, list)
        assert len(result) > 1
        for tweet in result:
            assert len(tweet) <= 280

    def test_hashtags_preserved(self):
        result = adapter.adapt("Great news! #AI #OpenClaw", "twitter")
        assert "#AI" in result or "#OpenClaw" in result


# ------------------------------------------------------------------
# LinkedIn
# ------------------------------------------------------------------
class TestLinkedInAdaptation:
    def test_returns_string(self):
        result = adapter.adapt("# My Article\n\nSome content here.", "linkedin")
        assert isinstance(result, str)

    def test_max_length(self):
        long = "word " * 1000
        result = adapter.adapt(long, "linkedin")
        assert len(result) <= 3000


# ------------------------------------------------------------------
# WeChat
# ------------------------------------------------------------------
class TestWeChatAdaptation:
    def test_returns_dict(self):
        result = adapter.adapt("# Title\n\nBody paragraph.", "wechat")
        assert isinstance(result, dict)
        assert "title" in result
        assert "content" in result

    def test_html_output(self):
        result = adapter.adapt("# Hello\n\nWorld", "wechat")
        assert "<h1>" in result["content"] or "<section" in result["content"]


# ------------------------------------------------------------------
# Xiaohongshu
# ------------------------------------------------------------------
class TestXiaohongshuAdaptation:
    def test_returns_dict(self):
        result = adapter.adapt("# My Note\n\nSome content", "xiaohongshu")
        assert isinstance(result, dict)
        assert "title" in result
        assert "desc" in result

    def test_max_length(self):
        long = "字" * 2000
        result = adapter.adapt(long, "xiaohongshu")
        assert len(result["desc"]) <= 1000


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
class TestHelpers:
    def test_strip_markdown(self):
        md = "## Heading\n\n**bold** and *italic*"
        result = ContentAdapter._strip_markdown(md)
        assert "##" not in result
        assert "**" not in result

    def test_extract_title(self):
        assert ContentAdapter._extract_title("# My Title\n\nBody") == "My Title"

    def test_extract_hashtags(self):
        tags = ContentAdapter._extract_hashtags("Hello #world #AI test")
        assert "#world" in tags
        assert "#AI" in tags

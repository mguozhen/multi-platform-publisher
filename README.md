# OpenClaw Skill: Multi-Platform Publisher

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An OpenClaw Skill to publish content to multiple social media platforms with a single command. This skill automatically adapts your content for each platform's constraints and audience, supporting text, images, and platform-specific features like Twitter/X threads.

**Author**: mguozhen

## Overview

The **Multi-Platform Publisher** skill streamlines your social media workflow by providing a unified interface to post updates across different channels. Instead of manually logging into each platform, adapting your content, and uploading media, you can do it all with one command from your OpenClaw agent.

The skill is designed to be highly configurable and extensible, using a modular adapter architecture that makes it easy to add new platforms in the future.

## Features

- **Multi-Platform Publishing**: Post to X/Twitter, LinkedIn, WeChat Official Account, and Xiaohongshu simultaneously.
- **Content Adaptation Engine**: Automatically reformats content for each platform's character limits, formatting rules, and tone.
- **Image Uploads**: Attach images to your posts on all supported platforms.
- **Platform-Specific Features**: Create Twitter/X threads for long-form content.
- **Flexible Configuration**: Configure API credentials securely via environment variables or your global `openclaw.json` file.
- **Command-Line Interface**: A simple and powerful CLI for publishing, validating credentials, and listing platforms.
- **Dry-Run Mode**: Preview how your content will be adapted and sent to each platform without actually publishing.

## Supported Platforms

The skill currently supports the following platforms, each with a dedicated adapter to handle its specific API and authentication method.

| Platform | Auth Method | Features |
|:---|:---|:---|
| **X/Twitter** | OAuth 1.0a | Tweets, Threads, Image Uploads |
| **LinkedIn** | OAuth 2.0 | Articles, Posts, Image Uploads |
| **WeChat Official Account** | API Token | Draft Creation, Image Uploads, HTML Content |
| **Xiaohongshu (小红书)** | MCP / Cookie | Note Publishing, Image Uploads |

## Installation

1.  **Clone the repository** or place the `multi-platform-publisher` directory into your OpenClaw skills folder:
    -   **Shared Skill**: `~/.openclaw/skills/`
    -   **Workspace Skill**: `<your_workspace>/skills/`

2.  **Install Python dependencies**:

    ```bash
    pip3 install -r /path/to/multi-platform-publisher/requirements.txt
    ```

    Or, if you have `uv` installed:

    ```bash
    uv pip install -r /path/to/multi-platform-publisher/requirements.txt
    ```

## Configuration

Credentials are required for each platform you wish to use. The skill loads configuration from multiple sources with the following precedence:

1.  **Environment Variables** (Highest priority)
2.  **OpenClaw Global Config** (`~/.openclaw/openclaw.json`)
3.  **Local `config.json`** (Not recommended for sensitive keys)

### Method 1: Environment Variables

Set the following environment variables for the platforms you want to enable:

```bash
# X/Twitter
export TWITTER_API_KEY="..."
export TWITTER_API_SECRET="..."
export TWITTER_ACCESS_TOKEN="..."
export TWITTER_ACCESS_TOKEN_SECRET="..."

# LinkedIn
export LINKEDIN_ACCESS_TOKEN="***"
export LINKEDIN_PERSON_URN="urn:li:person:..." # Optional, will be auto-detected
export LINKEDIN_CLIENT_ID="your-client-id"     # Optional, for OAuth app wiring
export LINKEDIN_CLIENT_SECRET="your-primary-secret"
export LINKEDIN_CLIENT_SECRET_SECONDARY="your-secondary-secret"
# If LINKEDIN_ACCESS_TOKEN accidentally contains a client secret that starts with WPL_AP1,
# the loader now ignores it and falls back to the token stored in openclaw.json.
# The adapter also uses LinkedIn-Version 202504 and sends a single-image payload when only one image is attached.

# WeChat Official Account
export WECHAT_APPID="..."
export WECHAT_APPSECRET="***"
# Note: WeChat draft cover images must use permanent thumb media.
# Inline article images should use local file paths so the adapter can upload them to mmbiz CDN automatically.

# Xiaohongshu
export XHS_COOKIE="..." # Your browser cookie
```

### Method 2: OpenClaw Global Config

Edit your `~/.openclaw/openclaw.json` file to add the credentials under the skill's entry. This is the recommended approach for managing keys within the OpenClaw ecosystem.

```json
{
  "skills": {
    "entries": {
      "multi-platform-publisher": {
        "enabled": true,
        "env": {
          "TWITTER_API_KEY": "your-key",
          "TWITTER_API_SECRET": "your-secret",
          "TWITTER_ACCESS_TOKEN": "your-token",
          "TWITTER_ACCESS_TOKEN_SECRET": "your-token-secret",
          "LINKEDIN_ACCESS_TOKEN": "your-linkedin-token",
          "WECHAT_APPID": "your-wechat-appid",
          "WECHAT_APPSECRET": "your-wechat-secret",
          "XHS_COOKIE": "your-xiaohongshu-cookie"
        }
      }
    }
  }
}
```

## Usage

The skill is invoked through its Python entrypoint, `main.py`. You can call it directly or through your OpenClaw agent if it's configured to use Python tools.

### Publish Content

**Publish inline content to all configured platforms:**
```bash
python3 {baseDir}/main.py publish --content "This is my new post about #AI and #OpenClaw!"
```

**Publish from a Markdown file to specific platforms:**
```bash
python3 {baseDir}/main.py publish --file ./my-article.md --platforms twitter,linkedin
```

**Publish with an image:**
```bash
python3 {baseDir}/main.py publish --content "Check out this photo!" --images ./photo.jpg
```

**Publish a long post as a Twitter/X thread:**
```bash
python3 {baseDir}/main.py publish --file ./long-article.md --platforms twitter --thread
```

**Preview a post without publishing (Dry Run):**
```bash
python3 {baseDir}/main.py publish --content "Test post" --dry-run
```

### Utility Commands

**List all available platforms and their status:**
```bash
python3 {baseDir}/main.py list-platforms
```

**Validate credentials for all configured platforms:**
```bash
python3 {baseDir}/main.py validate
```

## Development

### Project Structure

```
multi-platform-publisher/
├── adapters/           # Platform-specific logic (Twitter, LinkedIn, etc.)
├── utils/              # Shared utilities (content adaptation, config)
├── tests/              # Unit and integration tests
├── assets/             # Static assets (icons, etc.)
├── main.py             # CLI entrypoint and core orchestrator
├── SKILL.md            # OpenClaw skill definition
├── manifest.json       # Skill metadata
├── README.md           # This file
└── requirements.txt    # Python dependencies
```

### Running Tests

To run the included tests, you'll need `pytest`:

```bash
# Install pytest
python3 -m pip install pytest

# Run tests from the skill's root directory
python3 -m pytest
```

## License

This OpenClaw Skill is distributed under the **MIT License**. See the `LICENSE` file for more information.

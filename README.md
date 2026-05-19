<h1 align="center">Multi-Platform Publisher</h1>

<p align="center">
  <strong>One command. Every platform. Your content, auto-adapted.</strong><br>
  <em>Write once — get a Twitter thread, a LinkedIn post, a WeChat HTML draft, a Xiaohongshu note,<br>
  and a full self-media content pipeline behind it. Agent-native, 13 platforms, MIT.</em>
</p>

<p align="center">
  <a href="#quick-start"><img src="https://img.shields.io/badge/setup-60s-brightgreen?style=flat-square" alt="60s Setup"></a>
  <a href="#supported-platforms"><img src="https://img.shields.io/badge/platforms-13-FF6A00?style=flat-square" alt="13 platforms"></a>
  <a href="#the-super-writer-pipeline"><img src="https://img.shields.io/badge/pipeline-super--writer-blueviolet?style=flat-square" alt="super-writer pipeline"></a>
  <img src="https://img.shields.io/badge/python-%E2%89%A53.8-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.8+">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="MIT"></a>
</p>

---

## TL;DR

One piece of content in. Thirteen platform-native posts out.

```
                                  ┌───────────────────────────────┐
   ┌──────────────┐               │  content adaptation engine    │
   │  Markdown    │──┐            │  per-platform: length, format, │
   │  or inline   │  │            │  tone, hashtags, threads       │
   └──────────────┘  ├────────────▶───────────────────────────────┤
   ┌──────────────┐  │            │  API adapters   browser auto   │
   │  + images    │──┘            │  X · LinkedIn   HN · Reddit    │
   └──────────────┘               │  WeChat · XHS   note · Substack│
                                  └───────────────┬───────────────┘
                                                  │
        ┌─────────────────────────────────────────┼─────────────────────┐
        ▼                     ▼                   ▼                     ▼
   X / Twitter thread    LinkedIn post     WeChat HTML draft      Xiaohongshu note
   Dev.to · Qiita        YouTube           Hacker News · Reddit   note.com · Substack
```

- **Inputs** — a Markdown file or inline text, optional images
- **Engine** — `content_adapter.py` reshapes per platform (char limits, threads, HTML, emoji, tags)
- **Two layers** — a one-command **publisher** (`main.py` + API adapters) **and** the **super-writer** content pipeline (topic selection → AI draft → human review → publish)

---

## Quick start

### Option A — One-command publish (recommended)

```bash
# 1. Install
pip3 install -r requirements.txt

# 2. Set credentials for the platforms you want (env vars or ~/.openclaw/openclaw.json)
export TWITTER_API_KEY="..."   TWITTER_API_SECRET="..."
export TWITTER_ACCESS_TOKEN="..."   TWITTER_ACCESS_TOKEN_SECRET="..."
export LINKEDIN_ACCESS_TOKEN="..."
export WECHAT_APPID="..."   WECHAT_APPSECRET="..."
export XHS_COOKIE="..."

# 3. Publish
python3 main.py publish --file article.md --platforms all
```

### Option B — Preview first (dry run)

```bash
python3 main.py publish --content "My post about #AI" --dry-run
```

Shows exactly how the content will be reshaped for each platform — no posting.

### Option C — Ask your agent

In OpenClaw / Hermes / Claude Code, this ships as a Skill — just say:

> Publish `article.md` to Twitter and LinkedIn, and put a draft in WeChat.

The agent calls `main.py` and hands you the results.

### Utility commands

```bash
python3 main.py list-platforms   # show platforms + credential status
python3 main.py validate         # check credentials for every configured platform
```

---

## Supported platforms

Two surfaces. The **publisher** (`main.py`) covers four platforms over official APIs. The **super-writer pipeline** adds nine more through dedicated publishers.

| Platform | Surface | Auth | Output |
|---|---|---|---|
| **X / Twitter** | publisher | OAuth 1.0a | Tweets, threads, image + video upload |
| **LinkedIn** | publisher | OAuth 2.0 | Posts, articles, images |
| **WeChat Official Account** | publisher | API token | HTML article → draft box |
| **Xiaohongshu (小红书)** | publisher | Cookie | Image-text note |
| **Dev.to** | super-writer | REST API | English dev article |
| **Qiita** | super-writer | REST API | Japanese dev article |
| **YouTube** | super-writer | Data API v3 | Video + Shorts |
| **Hacker News** | super-writer | browser automation | Link / text submission |
| **Reddit** | super-writer | browser automation | Subreddit post |
| **note.com** | super-writer | browser automation | Japanese essay |
| **Substack** | super-writer | browser automation | English long-form + Notes |
| **抖音 / Douyin** | super-writer | browser automation | Short video |
| **视频号 / Channels** | super-writer | manual | 1–3 min video |

> Publishing red lines are respected: WeChat stops at the **draft box** (never auto-publishes), Xiaohongshu and Reddit run **human-in-the-loop**, and risky platforms surface a confirmation step. See `super-writer/playbooks/`.

---

## Content adaptation

The same source is reshaped, not just truncated:

- **X / Twitter** — strips Markdown, splits into 280-char tweets, builds numbered threads
- **LinkedIn** — professional register, clean paragraphs, up to 3,000 chars
- **WeChat** — styled HTML article rendered into a draft (manual publish in the dashboard)
- **Xiaohongshu** — casual tone, emoji injection, topic tags, 1,000-char cap
- **Dev.to / Qiita** — front-matter + tags, English / Japanese dev framing
- **Substack / note.com** — long-form essay + short Notes

---

## The super-writer pipeline

`super-writer/` is a complete one-person self-media production line:

```
topic gacha  →  AI draft (persona-locked)  →  cover + layout  →  Telegram review  →  multi-platform publish
```

- `super-writer/tools/gacha.py` — topic selector, aggregates 5 sources with scoring
- `super-writer/tools/telegram-bridge/` — human-in-the-loop review bridge + per-platform publishers
- `super-writer/tools/{hn,note,reddit}_publish.py` — browser-automation publishers for API-less platforms
- `super-writer/playbooks/` — 15 platform / content-type writing playbooks
- `super-writer/platform-roadmap.md` — live / queued / manual platform status
- `super-writer/persona.md` — account persona

---

## vs. the alternatives

| | **multi-platform-publisher** | Buffer / Hootsuite | Typefully | Manual posting |
|---|---|---|---|---|
| **Per-platform content adaptation** | ✅ reshapes tone + format | ⚠️ same text everywhere | ⚠️ Twitter-only | ✅ but by hand |
| **Agent-callable** | ✅ Skill / CLI | ❌ | ❌ | ❌ |
| **WeChat / Xiaohongshu / Dev.to / Qiita** | ✅ | ❌ | ❌ | ✅ |
| **Content pipeline (topic → draft → review)** | ✅ super-writer | ❌ | ❌ | ❌ |
| **Cost** | free, MIT | $6–99/mo | $12.50/mo | free |
| **Open source** | ✅ | ❌ | ❌ | — |

---

## Architecture

```
multi-platform-publisher/
├── main.py                    # CLI entrypoint + orchestrator
├── adapters/
│   ├── base_adapter.py        # abstract base: publish() / validate() / upload_image()
│   ├── twitter_adapter.py     # X / Twitter — OAuth 1.0a
│   ├── linkedin_adapter.py    # LinkedIn — OAuth 2.0
│   ├── wechat_adapter.py      # WeChat Official Account — API token
│   └── xiaohongshu_adapter.py # Xiaohongshu — cookie
├── utils/
│   ├── config_loader.py       # env > openclaw.json > config.json
│   ├── content_adapter.py     # per-platform content transformation
│   ├── image_handler.py       # resize / validate before upload
│   └── logger.py
├── super-writer/              # one-person self-media content pipeline
│   ├── tools/                 # gacha, telegram-bridge, per-platform publishers
│   ├── playbooks/             # 15 writing playbooks
│   ├── platform-roadmap.md
│   └── persona.md
├── podcasts/                  # sample podcast audio
├── tests/
├── SKILL.md                   # OpenClaw skill definition
└── manifest.json
```

- **Adapters** — each platform isolated behind `BaseAdapter`; adding one is a single file
- **Config precedence** — environment variables > `~/.openclaw/openclaw.json` > local `config.json`
- **Secrets** — never committed; `.env`, cookies, and browser profiles are gitignored

---

## Configuration

Credentials load with this precedence: **env vars → `~/.openclaw/openclaw.json` → `config.json`**.

```json
{
  "skills": {
    "entries": {
      "multi-platform-publisher": {
        "enabled": true,
        "env": {
          "TWITTER_API_KEY": "...",
          "LINKEDIN_ACCESS_TOKEN": "...",
          "WECHAT_APPID": "...",
          "XHS_COOKIE": "..."
        }
      }
    }
  }
}
```

See `config.json.example` for the full key list.

---

## Roadmap

- [x] 4 API adapters — X, LinkedIn, WeChat, Xiaohongshu
- [x] Content adaptation engine
- [x] super-writer content pipeline merged in
- [x] Browser-automation publishers — Hacker News, Reddit, note.com, Substack
- [ ] Promote super-writer publishers into first-class `adapters/`
- [ ] `npx skills add mguozhen/multi-platform-publisher` one-line install
- [ ] Scheduled / queued publishing

---

## Development

```bash
python3 -m pip install pytest
python3 -m pytest
```

---

## License

MIT — see [LICENSE](LICENSE).

**Author**: [mguozhen](https://github.com/mguozhen)

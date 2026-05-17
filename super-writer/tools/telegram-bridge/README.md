# Telegram Approval Bridge

Human-in-the-loop via Telegram. Your agent pushes a draft → you tap a button.

```
✅ Approve  → run execute() hook (post / send / commit)
🔄 Regen    → run generate() hook, replace the draft
❌ Reject   → bot asks "why?", saves the reason, auto-regenerates
             with that reason injected as "AVOID THIS" in the next prompt
```

The reject → reason → negative-few-shot loop is the point. The system
learns from every "no".

## Files

```
telegram.py          urllib-only Bot API wrapper
bridge.py            queue + long-poll loop + CLI
hooks_demo.py        demo hooks (publishes nothing — proves the loop)
hooks_selfmedia.py   real hooks (xhs / linkedin / x)
queue.json           the draft queue (auto-created)
.env                 config (copy from .env.example)
```

## Setup (5 min)

```bash
# 1. create a bot
#    Telegram → @BotFather → /newbot → copy the token

# 2. config
cp .env.example .env
#    paste TELEGRAM_BOT_TOKEN into .env

# 3. DM your new bot "hi" on Telegram

# 4. discover your chat_id
python3 bridge.py --discover-chat
#    paste the printed chat_id into .env as TELEGRAM_CHAT_ID

# 5. run the loop (keep alive — tmux / nohup / launchd)
python3 bridge.py --run
```

## Test with demo hooks

```bash
# .env has BRIDGE_HOOKS=hooks_demo
python3 bridge.py --run          # terminal 1

# terminal 2 — push a test draft
python3 bridge.py --enqueue --label "test" \
    --draft "hello from the bridge" \
    --context '{"topic":"the bridge itself"}'

# → card appears in Telegram. Tap Reject, type a reason,
#   watch it auto-regen with "(avoiding: <your reason>)".
```

## Go live (self-media)

```bash
# in .env:
BRIDGE_HOOKS=hooks_selfmedia
LLM_API_KEY=<flatkey key>

# enqueue a real post:
python3 bridge.py --enqueue --label "XHS post" \
    --draft "$(cat draft.txt)" \
    --context '{"platform":"xhs","topic":"...","title":"...","tags":"AI,ClaudeCode","image":"/path.png"}'
```

`execute()` routes by `context.platform`:
- `xhs`      → xhs-mcp CLI (working)
- `linkedin` → li-post.py (needs `~/.secrets/linkedin.env`)
- `x`        → staged to a file for manual post (X auto-post pending)

## Writing your own hooks

Any module with two functions:

```python
def generate(entry: dict) -> str:
    # entry["rejection_reasons"] is a list — feed it as negative examples
    return new_draft_text

def execute(entry: dict) -> dict:
    return {"ok": True, "url": "...", "detail": "..."}   # or {"ok": False, "error": "..."}
```

Point `BRIDGE_HOOKS` env var at the module name.

## Gotchas (handled, but know them)

- `answerCallbackQuery` is always called — buttons never hang.
- All updates filtered by `chat_id` — strangers can't trigger anything.
- `callback_data` is `a:/g:/r:` + a 6-hex id — well under the 64-byte cap.
- Long-poll offset persisted in `.bridge_state.json` — survives restarts.
- A frozen card (buttons removed) means it reached a terminal state.

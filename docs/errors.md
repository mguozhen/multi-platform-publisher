# multi-platform-publisher — Semantic Error Reference

Every MCP tool returns errors in a structured shape so an Agent can self-heal.

```json
{
  "error": {
    "type": "auth_missing",
    "message": "twitter credentials not configured.",
    "suggested_action": "Set TWITTER_API_KEY / TWITTER_API_SECRET / TWITTER_ACCESS_TOKEN / TWITTER_ACCESS_TOKEN_SECRET as env vars, or list them under skills.entries.multi-platform-publisher.env in ~/.openclaw/openclaw.json.",
    "retryable": false,
    "docs_url": "https://github.com/mguozhen/multi-platform-publisher/blob/main/docs/errors.md#auth_missing"
  }
}
```

`publish_to_platforms` returns a per-platform result map — one platform's error never blocks the others. Inspect `results[platform].ok` and `results[platform].error`.

## Error table

| `type` | When it happens | `retryable` | `suggested_action` |
|---|---|---|---|
| `invalid_input` | Neither `content` nor `file_path` supplied (or file doesn't exist) | no | Pass one of `content` (inline text) or `file_path` (path to a `.md` / `.txt` that exists). |
| `unknown_platform` | `platform` not in the registry | no | Call `list_supported_platforms()` for valid ids. Common aliases: `x`→`twitter`, `xhs`→`xiaohongshu`. |
| `auth_missing` | Required credentials for a platform aren't set | no | Set the env vars listed in `agent-capabilities.json#auth.per_platform_required`, or put them under `~/.openclaw/openclaw.json`. |
| `publish_failed` | Platform adapter raised at publish time (API 5xx, network, etc.) | yes | Retry once after 5-10s. If it persists, check the platform's status page and re-validate credentials. |
| `wechat_draft_only` | (Soft signal — not really an error) WeChat returns a `draft_id` not a public URL | n/a | This is the safety contract. Open WeChat Official Account dashboard → Drafts → review → publish manually. |
| `xhs_login_expired` | Xiaohongshu cookie expired | no | Re-export the cookie and update `XHS_COOKIE`. XHS sessions are short-lived. |
| `image_too_large` | An image exceeded the platform's max size | no | `utils/image_handler.py` will resize automatically — if this still fires, the input was unreadable. Re-export the image. |

## Recovery contract for Agents

1. `retryable: true` → retry with backoff (5-10s for `publish_failed`). Cap at 2 attempts per platform.
2. `retryable: false` → do **not** retry the same call. Execute the `suggested_action` (it names the exact fix).
3. `publish_to_platforms` returns a partial-success map — treat platform-level failures independently and surface the per-platform error to the user, not the whole call.
4. WeChat's `draft_only` result is **success, not failure** — the safety design is to never auto-publish to a public WeChat OA. Tell the user "draft created" and link them to the dashboard.

## Why semantic errors

A naive cross-poster fails opaquely and the Agent gives up. `publish_to_platforms` returns per-platform results with structured errors so the Agent can react precisely: retry the LinkedIn 5xx, alert the user that the XHS cookie expired, and ship the Twitter post that succeeded — all in one call.

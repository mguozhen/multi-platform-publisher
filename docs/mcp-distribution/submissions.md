# MCP catalog distribution — multi-platform-publisher

Paste-ready submission package for the 5 major MCP catalogs.

## Status tracker

| Catalog | Mechanism | Status | Note |
|---|---|---|---|
| awesome-mcp-servers (punkpeye) | GitHub PR | ❌ todo | submit under category Social/Productivity |
| cline/mcp-marketplace | GitHub PR | ❌ todo | |
| glama.ai | auto-index | 🟢 auto | indexes public GitHub repos with MCP metadata |
| mcp.so | web form | ❌ todo | needs OAuth — 5 min |
| smithery.ai | web form / `smithery.yaml` | ❌ todo | needs OAuth |
| pulsemcp.com | web form | ❌ todo | needs OAuth |
| Official MCP Registry | `server.json` + OIDC | ❌ blocked | needs `multi-platform-publisher` on PyPI first |

## Shared blurb (paste into any catalog)

**Name:** multi-platform-publisher
**Category:** Social / Publishing / Productivity  *(not "AI" — this is a vertical capability for content distribution)*
**One-liner:** Write once, publish everywhere — X / LinkedIn / WeChat / Xiaohongshu in one MCP call, with real per-platform adaptation.
**Description:**
> One MCP server, 4 tools, 13 platforms. Takes a single source (markdown or
> inline text + optional images) and adapts it per platform: Twitter threads
> with numbering, LinkedIn paragraphs, WeChat HTML drafts, Xiaohongshu emoji
> + tags. Includes a dry-run preview tool so an Agent can show the user
> exactly what each platform will receive before posting. Per-platform
> failures are isolated. MIT-licensed. Plus the bundled super-writer pipeline
> adds Dev.to, Qiita, HN, Reddit, note.com, Substack, YouTube, Douyin, and
> Channels through dedicated publishers.

**Install:** `claude mcp add mpp -- python -m mcp_server`
**Repo:** https://github.com/mguozhen/multi-platform-publisher
**Tags:** mcp, social-media, cross-post, twitter, linkedin, wechat, xiaohongshu, content-publishing

## Per-catalog notes

- **mcp.so / pulsemcp** — web form, shared blurb, category **Social / Productivity**.
- **smithery.ai** — supports stdio servers; commit a `smithery.yaml` or use the form. Mark every `*_API_KEY` / `*_TOKEN` / `XHS_COOKIE` as required-only-if-you-want-that-platform (per-platform optional).
- **Official MCP Registry** — publish `multi-platform-publisher` to PyPI, then `mcp-publisher publish` with the `server.json` in this directory.

## The Discovery principle

multi-platform-publisher is a **vertical** capability (cross-platform publishing). Catalog category should be **Social / Productivity**, never the generic "AI" bucket. An Agent doing publishing work filters by domain category — be in the right one.

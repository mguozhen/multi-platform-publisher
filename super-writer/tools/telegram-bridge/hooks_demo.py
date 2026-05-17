"""
Demo hooks — proves the bridge works without any real integration.

Two functions every hooks module must define:
  generate(entry) -> str          new draft text
  execute(entry)  -> dict          {"ok": bool, "error"?: str, "url"?: str}

Swap BRIDGE_HOOKS env var to point at your real hooks module.
"""
import time


def generate(entry: dict) -> str:
    """Re-generate a draft. Honors rejection_reasons as negative examples."""
    topic = entry.get("context", {}).get("topic", "something")
    reasons = entry.get("rejection_reasons", [])
    draft = f"[demo draft v{len(reasons) + 1}] a post about {topic}, generated {time.strftime('%H:%M:%S')}"
    if reasons:
        # THE MAGIC PART — last "no" steers the next draft
        draft += f"\n(avoiding: {reasons[-1]})"
    return draft


def execute(entry: dict) -> dict:
    """Pretend to publish. Real hooks would actually post / send / commit."""
    print(f"[demo execute] would publish entry {entry['id']}: {entry['draft_text'][:60]}")
    return {"ok": True, "detail": "demo: nothing actually published"}

"""
Minimal Telegram Bot API wrapper — urllib only, zero dependencies.

Exposes exactly what the approval bridge needs:
  send_card(token, chat_id, entry)        -> message_id
  edit_card(token, chat_id, entry, footer=None, buttons=True) -> None
  answer_callback(token, callback_query_id, text="") -> None
  get_updates(token, offset=None, timeout=25) -> list[update]
"""
from __future__ import annotations

import json
import time
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

API = "https://api.telegram.org/bot{token}/{method}"


def _call(token: str, method: str, params: dict, timeout: int = 30) -> dict:
    """POST to the Telegram Bot API. Returns the parsed `result` field."""
    url = API.format(token=token, method=method)
    data = json.dumps(params).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        raise RuntimeError(f"Telegram {method} HTTP {e.code}: {body}") from e
    if not payload.get("ok"):
        raise RuntimeError(f"Telegram {method} failed: {payload}")
    return payload.get("result")


def _keyboard(entry_id: str) -> dict:
    """3 inline buttons. callback_data kept short (<64 bytes): a:/g:/r: + id."""
    return {
        "inline_keyboard": [[
            {"text": "✅ Approve", "callback_data": f"a:{entry_id}"},
            {"text": "🔄 Regen",   "callback_data": f"g:{entry_id}"},
            {"text": "❌ Reject",  "callback_data": f"r:{entry_id}"},
        ]]
    }


def _render(entry: dict, footer: str | None = None) -> str:
    """Build the card body text. Plain text — body may contain _ * ` etc."""
    head = f"📝 Draft {entry['id']}"
    label = entry.get("label")
    if label:
        head += f" — {label}"
    body = entry.get("draft_text", "")
    text = f"{head}\n\n{body}"
    if footer:
        text += f"\n\n———\n{footer}"
    return text


def send_card(token: str, chat_id: str, entry: dict) -> int:
    """Send a fresh approval card. Returns telegram message_id."""
    result = _call(token, "sendMessage", {
        "chat_id": chat_id,
        "text": _render(entry),
        "reply_markup": _keyboard(entry["id"]),
        "disable_web_page_preview": True,
    })
    return result["message_id"]


def edit_card(token: str, chat_id: str, entry: dict,
              footer: str | None = None, buttons: bool = True) -> None:
    """Edit an existing card in place. Set buttons=False to freeze it (terminal state)."""
    params = {
        "chat_id": chat_id,
        "message_id": entry["telegram_message_id"],
        "text": _render(entry, footer),
        "disable_web_page_preview": True,
    }
    if buttons:
        params["reply_markup"] = _keyboard(entry["id"])
    else:
        params["reply_markup"] = {"inline_keyboard": []}
    try:
        _call(token, "editMessageText", params)
    except RuntimeError as e:
        # "message is not modified" is harmless
        if "not modified" not in str(e):
            raise


def answer_callback(token: str, callback_query_id: str, text: str = "") -> None:
    """ALWAYS call this after a callback, or the button spinner hangs."""
    try:
        _call(token, "answerCallbackQuery", {
            "callback_query_id": callback_query_id,
            "text": text[:200],
        })
    except RuntimeError:
        pass  # never let a callback-ack failure break the loop


def send_message(token: str, chat_id: str, text: str) -> int:
    result = _call(token, "sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    })
    return result["message_id"]


# ── generic custom-button messages (used by the 抽卡 / 选平台 / 选 playbook flow) ──
def _kb(button_rows: list) -> dict:
    """button_rows = [[(label, callback_data), ...], ...]"""
    return {
        "inline_keyboard": [
            [{"text": lbl, "callback_data": cd} for (lbl, cd) in row]
            for row in button_rows
        ]
    }


def send_buttons(token: str, chat_id: str, text: str, button_rows: list,
                 markdown: bool = True) -> int:
    """Send a message with an arbitrary inline-keyboard layout. Returns message_id.

    markdown=False for text with raw _ * ` (filenames, captions).
    """
    params = {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": _kb(button_rows),
        "disable_web_page_preview": True,
    }
    if markdown:
        params["parse_mode"] = "Markdown"
    result = _call(token, "sendMessage", params)
    return result["message_id"]


def edit_buttons(token: str, chat_id: str, message_id: int, text: str,
                 button_rows: list | None = None, markdown: bool = True) -> None:
    """Edit a message + its keyboard. button_rows=None freezes it (no buttons)."""
    params = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "disable_web_page_preview": True,
        "reply_markup": _kb(button_rows) if button_rows else {"inline_keyboard": []},
    }
    if markdown:
        params["parse_mode"] = "Markdown"
    try:
        _call(token, "editMessageText", params)
    except RuntimeError as e:
        if "not modified" not in str(e):
            raise


def send_photo(token: str, chat_id: str, image_path: str,
               caption: str = "") -> int:
    """上传一张本地图片到 chat (multipart)。返回 message_id。"""
    p = Path(image_path)
    boundary = "----tgphoto" + str(int(time.time() * 1000))
    body = bytearray()

    def _field(name: str, value: str) -> None:
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        body.extend(f"{value}\r\n".encode())

    _field("chat_id", str(chat_id))
    if caption:
        _field("caption", caption[:1024])
    body.extend(f"--{boundary}\r\n".encode())
    body.extend((f'Content-Disposition: form-data; name="photo"; '
                 f'filename="{p.name}"\r\n').encode())
    body.extend(b"Content-Type: application/octet-stream\r\n\r\n")
    body.extend(p.read_bytes())
    body.extend(f"\r\n--{boundary}--\r\n".encode())

    url = API.format(token=token, method="sendPhoto")
    req = urllib.request.Request(
        url, data=bytes(body), method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if not payload.get("ok"):
        raise RuntimeError(f"sendPhoto failed: {payload}")
    return payload["result"]["message_id"]


def download_file(token: str, file_id: str, dest_dir: str) -> Path:
    """getFile + 下载到 dest_dir。返回本地路径。

    ⚠️ Telegram Bot API getFile 下载上限 20MB — 超了会抛 RuntimeError。
    """
    info = _call(token, "getFile", {"file_id": file_id})
    file_path = info.get("file_path")
    if not file_path:
        raise RuntimeError(f"getFile 无 file_path: {info}")
    url = f"https://api.telegram.org/file/bot{token}/{file_path}"
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    name = Path(file_path).name or f"tg-{int(time.time())}"
    out = dest / name
    try:
        with urllib.request.urlopen(url, timeout=180) as r:
            out.write_bytes(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(
            f"下载失败 HTTP {e.code} — 文件可能超过 Telegram 20MB 下载上限") from e
    return out


def send_document(token: str, chat_id: str, file_path: str,
                  caption: str = "") -> int:
    """以文件形式发送（不压缩、不受图片尺寸限制）。返回 message_id。"""
    p = Path(file_path)
    boundary = "----tgdoc" + str(int(time.time() * 1000))
    body = bytearray()

    def _field(name: str, value: str) -> None:
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        body.extend(f"{value}\r\n".encode())

    _field("chat_id", str(chat_id))
    if caption:
        _field("caption", caption[:1024])
    body.extend(f"--{boundary}\r\n".encode())
    body.extend((f'Content-Disposition: form-data; name="document"; '
                 f'filename="{p.name}"\r\n').encode())
    body.extend(b"Content-Type: application/octet-stream\r\n\r\n")
    body.extend(p.read_bytes())
    body.extend(f"\r\n--{boundary}--\r\n".encode())

    url = API.format(token=token, method="sendDocument")
    req = urllib.request.Request(
        url, data=bytes(body), method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if not payload.get("ok"):
        raise RuntimeError(f"sendDocument failed: {payload}")
    return payload["result"]["message_id"]


def get_updates(token: str, offset: int | None = None, timeout: int = 25) -> list:
    """Long-poll for updates. timeout is the server-side long-poll window."""
    params = {"timeout": timeout,
              "allowed_updates": ["message", "callback_query"]}
    if offset is not None:
        params["offset"] = offset
    # client timeout must exceed server long-poll window
    return _call(token, "getUpdates", params, timeout=timeout + 10)

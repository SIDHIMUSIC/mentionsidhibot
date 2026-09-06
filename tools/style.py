"""Small-caps, premium emoji, buttons, Bot API send helpers."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import urllib.error
import urllib.request

from telethon import Button
from telethon.tl.types import (
    MessageEntityBold,
    MessageEntityCustomEmoji,
    MessageEntityItalic,
    MessageEntityMentionName,
    MessageEntityStrike,
    MessageEntityTextUrl,
    MessageEntityUnderline,
)

from config import CONFIG

log = logging.getLogger("mentionbot")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
PE_NAMES = dict(CONFIG.get("pe_names") or {})
PREMIUM_EMOJI_IDS = list(CONFIG.get("premium_emoji_ids") or PE_NAMES.values())
LINE_EMOJI_IDS = list(CONFIG.get("line_emoji_ids") or [6285315214673975495, 6257814874085136842])
FALLBACK = "\u2728"
SC = str.maketrans(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "\u1d00\u0299\u1d04\u1d05\u1d07\ua730\u0262\u029c\u026a\u1d0a\u1d0b\u029f\u1d0d\u0274\u1d0f\u1d18\u01eb\u0280\ua731\u1d1b\u1d1c\u1d20\u1d21x\u028f\u1d22\u1d00\u0299\u1d04\u1d05\u1d07\ua730\u0262\u029c\u026a\u1d0a\u1d0b\u029f\u1d0d\u0274\u1d0f\u1d18\u01eb\u0280\ua731\u1d1b\u1d1c\u1d20\u1d21x\u028f\u1d22",
)
PROTECT_RE = re.compile(r"(/[A-Za-z_]+|\{[A-Za-z_]+\}|https?://[^\s]+|t\.me/[^\s]+|@\w+)")


def sc(text: str) -> str:
    return (text or "").translate(SC)

def sty(text: str) -> str:
    return sc(text)

def utf16_len(text: str) -> int:
    return len((text or "").encode("utf-16-le")) // 2

def emoji_id(i: int) -> int:
    return PREMIUM_EMOJI_IDS[i % len(PREMIUM_EMOJI_IDS)] if PREMIUM_EMOJI_IDS else 0

def line_emoji_id(i: int) -> int:
    ids = LINE_EMOJI_IDS or PREMIUM_EMOJI_IDS
    return ids[i % len(ids)] if ids else 0

def pe_icon(name: str | None) -> int:
    if name and name in PE_NAMES:
        return int(PE_NAMES[name])
    ids = PREMIUM_EMOJI_IDS
    if not ids:
        return 0
    seed = name or "btn"
    return int(ids[sum(ord(c) for c in seed) % len(ids)])

def btn(text: str, callback_data=None, url=None, pe_name=None, style=None) -> dict:
    key = pe_name or (text or "btn").strip().lower().replace(" ", "_")
    return {"text": sc(text), "data": callback_data, "url": url, "icon": pe_icon(key), "style": style}

def markup_json(rows) -> dict:
    keyboard = []
    for row in rows or []:
        line = []
        for item in row:
            cell = {"text": item.get("text") or ""}
            if item.get("url"):
                cell["url"] = item["url"]
            elif item.get("data") is not None:
                data = item["data"]
                cell["callback_data"] = data if isinstance(data, str) else data.decode()
            icon = item.get("icon") or pe_icon(item.get("text"))
            if icon:
                cell["icon_custom_emoji_id"] = str(icon)
            if item.get("style"):
                cell["style"] = item["style"]
            line.append(cell)
        keyboard.append(line)
    return {"inline_keyboard": keyboard}

def dict_rows(rows) -> bool:
    return bool(rows and rows[0] and isinstance(rows[0][0], dict))

def tele_buttons(rows):
    if not dict_rows(rows):
        return rows
    out = []
    for row in rows or []:
        line = []
        for item in row:
            label = item.get("text") or ""
            if item.get("url"):
                line.append(Button.url(label, item["url"]))
            else:
                data = item.get("data") or "x"
                if isinstance(data, str):
                    data = data.encode()
                line.append(Button.inline(label, data))
        out.append(line)
    return out

def ents_to_api(ents) -> list[dict]:
    api = []
    for ent in ents or []:
        if isinstance(ent, MessageEntityCustomEmoji):
            api.append({"type": "custom_emoji", "offset": ent.offset, "length": ent.length, "custom_emoji_id": str(ent.document_id)})
        elif isinstance(ent, MessageEntityMentionName):
            api.append({"type": "text_mention", "offset": ent.offset, "length": ent.length, "user": {"id": int(ent.user_id)}})
        elif isinstance(ent, MessageEntityTextUrl):
            url = ent.url or ""
            if url.startswith("tg://user?id="):
                try:
                    uid = int(url.split("id=")[-1])
                    api.append({"type": "text_mention", "offset": ent.offset, "length": ent.length, "user": {"id": uid}})
                    continue
                except ValueError:
                    pass
            api.append({"type": "text_link", "offset": ent.offset, "length": ent.length, "url": url})
        elif isinstance(ent, MessageEntityBold):
            api.append({"type": "bold", "offset": ent.offset, "length": ent.length})
        elif isinstance(ent, MessageEntityItalic):
            api.append({"type": "italic", "offset": ent.offset, "length": ent.length})
    return api

async def botapi(method: str, payload: dict) -> dict:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    def _call():
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "ignore")
            log.warning("botapi %s %s %s", method, exc.code, body[:300])
            return {"ok": False, "description": body}
    return await asyncio.to_thread(_call)

def dump_ents(entities, shift: int = 0) -> list[dict]:
    out = []
    for ent in entities or []:
        off = int(getattr(ent, "offset", 0)) - shift
        length = int(getattr(ent, "length", 0))
        if length <= 0 or off + length <= 0:
            continue
        if off < 0:
            length += off
            off = 0
        item = {"off": off, "len": length}
        if isinstance(ent, MessageEntityCustomEmoji):
            item["t"] = "emoji"; item["id"] = int(ent.document_id)
        elif isinstance(ent, MessageEntityMentionName):
            item["t"] = "mention"; item["uid"] = int(ent.user_id)
        elif isinstance(ent, MessageEntityTextUrl):
            item["t"] = "url"; item["url"] = ent.url
        elif isinstance(ent, MessageEntityBold):
            item["t"] = "bold"
        elif isinstance(ent, MessageEntityItalic):
            item["t"] = "italic"
        elif isinstance(ent, MessageEntityUnderline):
            item["t"] = "underline"
        elif isinstance(ent, MessageEntityStrike):
            item["t"] = "strike"
        else:
            continue
        out.append(item)
    return out

def load_ents(items) -> list:
    ents = []
    for item in items or []:
        kind, off, length = item.get("t"), int(item.get("off", 0)), int(item.get("len", 0))
        if length <= 0:
            continue
        if kind == "emoji" and item.get("id"):
            ents.append(MessageEntityCustomEmoji(off, length, int(item["id"])))
        elif kind == "mention" and item.get("uid"):
            ents.append(MessageEntityMentionName(off, length, int(item["uid"])))
        elif kind == "url" and item.get("url"):
            url = item["url"]
            if str(url).startswith("tg://user?id="):
                try:
                    ents.append(MessageEntityMentionName(off, length, int(str(url).split("id=")[-1])))
                    continue
                except ValueError:
                    pass
            ents.append(MessageEntityTextUrl(off, length, url))
        elif kind == "bold":
            ents.append(MessageEntityBold(off, length))
        elif kind == "italic":
            ents.append(MessageEntityItalic(off, length))
        elif kind == "underline":
            ents.append(MessageEntityUnderline(off, length))
        elif kind == "strike":
            ents.append(MessageEntityStrike(off, length))
    return ents

def shift_saved_ents(items, start16: int, old16: int, new16: int) -> list[dict]:
    delta = new16 - old16
    end16 = start16 + old16
    out = []
    for item in items or []:
        cur = dict(item)
        off = int(cur.get("off", 0))
        last = off + int(cur.get("len", 0))
        if last <= start16:
            out.append(cur)
        elif off >= end16:
            cur["off"] = off + delta
            out.append(cur)
    return out

def sc_keep(text: str) -> str:
    text = text or ""
    parts, last = [], 0
    for match in PROTECT_RE.finditer(text):
        parts.append(sc(text[last:match.start()]))
        parts.append(match.group(0))
        last = match.end()
    parts.append(sc(text[last:]))
    return "".join(parts)

def _is_start_caption(text: str) -> bool:
    low = (text or "").lower().replace("ɪ", "i").replace("ꜱ", "s").replace("ᴇ", "e")
    compact = low.replace(" ", "")
    return ("its me" in low) or ("smart tag bot" in low) or ("itsme" in compact)

def rich(text: str, start: int = 0):
    raw = text or ""
    skip_arrows = _is_start_caption(raw)
    text = sc_keep(raw)
    if skip_arrows:
        return text, []
    out, ents, n = "", [], start
    for i, line in enumerate(text.split("\n")):
        if i:
            out += "\n"
        if not line.strip():
            continue
        off = utf16_len(out)
        out += FALLBACK
        ents.append(MessageEntityCustomEmoji(off, utf16_len(FALLBACK), line_emoji_id(n)))
        n += 1
        out += " " + line
    return out, ents

async def say(client, target, text: str, buttons=None, reply_to=None):
    body, ents = rich(text)
    chat = getattr(target, "chat_id", target)
    rows = buttons
    if dict_rows(rows):
        result = await botapi("sendMessage", {"chat_id": chat, "text": body, "entities": ents_to_api(ents), "link_preview_options": {"is_disabled": True}, "reply_markup": markup_json(rows)})
        if result.get("ok"):
            return result
    kwargs = {"formatting_entities": ents, "link_preview": False}
    if rows is not None:
        kwargs["buttons"] = tele_buttons(rows) if dict_rows(rows) else rows
    if reply_to is not None:
        kwargs["reply_to"] = reply_to
    return await client.send_message(chat, body, **kwargs)

async def send_cancel(client, chat_id: int, user_id: int, name: str) -> None:
    name = (name or "user").strip() or "user"
    label = sc("cancel by ")
    text = FALLBACK + " " + label + name
    ents = [
        MessageEntityCustomEmoji(0, utf16_len(FALLBACK), line_emoji_id(0)),
        MessageEntityMentionName(utf16_len(FALLBACK + " " + label), utf16_len(name), int(user_id)),
    ]
    result = await botapi("sendMessage", {"chat_id": chat_id, "text": text, "entities": ents_to_api(ents), "link_preview_options": {"is_disabled": True}})
    if result.get("ok"):
        return
    await client.send_message(chat_id, text, formatting_entities=ents, link_preview=False)

async def edit_say(event, text: str, buttons=None):
    body, ents = rich(text)
    rows = buttons
    markup = markup_json(rows) if dict_rows(rows) else None
    msg = getattr(event, "message", None)
    has_media = bool(getattr(msg, "media", None) or getattr(msg, "photo", None))
    payload = {"chat_id": event.chat_id, "message_id": event.message_id}
    if markup:
        payload["reply_markup"] = markup
    if has_media:
        payload["caption"] = body
        payload["caption_entities"] = ents_to_api(ents)
        result = await botapi("editMessageCaption", payload)
    else:
        payload["text"] = body
        payload["entities"] = ents_to_api(ents)
        payload["link_preview_options"] = {"is_disabled": True}
        result = await botapi("editMessageText", payload)
    if result.get("ok"):
        return result
    if has_media:
        payload.pop("caption", None)
        payload.pop("caption_entities", None)
        payload["text"] = body
        payload["entities"] = ents_to_api(ents)
        payload["link_preview_options"] = {"is_disabled": True}
        result = await botapi("editMessageText", payload)
    else:
        payload.pop("text", None)
        payload.pop("entities", None)
        payload["caption"] = body
        payload["caption_entities"] = ents_to_api(ents)
        result = await botapi("editMessageCaption", payload)
    if result.get("ok"):
        return result
    if markup:
        return await botapi("editMessageReplyMarkup", {"chat_id": event.chat_id, "message_id": event.message_id, "reply_markup": markup})
    return result

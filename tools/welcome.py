"""Welcome message save + send."""

from __future__ import annotations

import logging
import re
import time

from telethon.tl.types import User

from tools.store import DATA_DIR, DEFAULT_WELCOME, gset, uset
from tools.style import (
    FALLBACK,
    btn,
    botapi,
    dump_ents,
    emoji_id,
    ents_to_api,
    load_ents,
    markup_json,
    shift_saved_ents,
    tele_buttons,
    utf16_len,
)

log = logging.getLogger("mentionbot")
PLACE_RE = re.compile(
    r"\{(mention|username|first_name|name|id|title|chatname|chat_name|group)\}",
    re.I,
)
BTN_RE = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")
welcome_seen: dict[str, float] = {}


def fill_welcome(template: str, saved_ents, values: dict, user: User):
    text = template or DEFAULT_WELCOME
    ents = [dict(x) for x in (saved_ents or [])]
    while True:
        match = PLACE_RE.search(text)
        if not match:
            break
        key = match.group(1).lower()
        start = match.start()
        token = match.group(0)
        start16 = utf16_len(text[:start])
        old16 = utf16_len(token)
        extra = None
        if key == "mention":
            repl = values["first_name"]
            extra = {"t": "url", "off": start16, "len": utf16_len(repl), "url": f"tg://user?id={user.id}"}
        elif key == "username":
            repl = values["username"]
        elif key in {"first_name", "name"}:
            repl = values["first_name"]
        elif key == "id":
            repl = values["id"]
        else:
            repl = values["chatname"]
        text = text[:start] + repl + text[match.end():]
        ents = shift_saved_ents(ents, start16, old16, utf16_len(repl))
        if extra:
            ents.append(extra)
    return text, load_ents(ents)


def add_line_premium(text: str, ents):
    if ents and hasattr(ents[0], "offset"):
        saved = dump_ents(ents)
    else:
        saved = [dict(x) for x in (ents or [])]
    starts = [0]
    for idx, ch in enumerate(text or ""):
        if ch == "\n":
            starts.append(idx + 1)
    n = len(starts) - 1
    for start in reversed(starts):
        nxt = text.find("\n", start)
        line = text[start:] if nxt < 0 else text[start:nxt]
        if not line.strip():
            n -= 1
            continue
        start16 = utf16_len(text[:start])
        piece = FALLBACK + " "
        text = text[:start] + piece + text[start:]
        saved = shift_saved_ents(saved, start16, 0, utf16_len(piece))
        saved.append({"t": "emoji", "off": start16, "len": utf16_len(FALLBACK), "id": emoji_id(max(n, 0))})
        n -= 1
    return text, load_ents(saved)


def setwelcome_prefix(raw: str) -> str:
    match = re.match(r"^/setwelcome(?:@\w+)?\s*", raw or "", flags=re.I)
    return match.group(0) if match else ""


async def grab_welcome_media(client, chat_id: int, message) -> str:
    if not message or not getattr(message, "media", None):
        return ""
    dest = DATA_DIR / f"welcome_{chat_id}"
    try:
        path = await client.download_media(message, file=str(dest))
        return str(path or "")
    except Exception as exc:
        log.warning("welcome media save: %s", exc)
        return ""


def parse_welcome_buttons(items):
    if not items:
        return None
    row = []
    for item in items[:6]:
        if isinstance(item, dict) and item.get("url"):
            row.append(btn(item.get("text") or "link", url=item["url"], pe_name="add"))
    return [row] if row else None


async def send_welcome(client, chat_id: int, user: User, title: str = "", force: bool = False) -> None:
    key = f"{chat_id}:{user.id}"
    now = time.time()
    if not force and now - welcome_seen.get(key, 0) < 8:
        return
    welcome_seen[key] = now
    s = gset(chat_id)
    if not s.get("welcome"):
        return
    first = user.first_name or "member"
    uname = f"@{user.username}" if user.username else first
    custom = bool(s.get("welcome_custom"))
    raw = (s.get("welcome_text") if custom else DEFAULT_WELCOME) or DEFAULT_WELCOME
    values = {"first_name": first, "username": uname, "id": str(user.id), "chatname": title or "group"}
    saved = s.get("welcome_entities") if custom else []
    text, ents = fill_welcome(raw, saved or [], values, user)
    if custom:
        text, ents = add_line_premium(text, ents)
    if s.get("cleanwelcome") and s.get("welcome_last") and not force:
        try:
            await client.delete_messages(chat_id, int(s["welcome_last"]))
        except Exception:
            pass
    btns = parse_welcome_buttons(s.get("welcome_buttons") or [])
    media = s.get("welcome_media") or ""
    try:
        payload = {"chat_id": chat_id}
        if media and str(media).startswith("http"):
            payload.update({"photo": media, "caption": text, "caption_entities": ents_to_api(ents)})
            if btns:
                payload["reply_markup"] = markup_json(btns)
            result = await botapi("sendPhoto", payload)
        else:
            payload.update({"text": text, "entities": ents_to_api(ents), "link_preview_options": {"is_disabled": True}})
            if btns:
                payload["reply_markup"] = markup_json(btns)
            result = await botapi("sendMessage", payload)
        if result.get("ok"):
            if not force:
                uset(chat_id, welcome_last=result["result"]["message_id"])
            return
        if media:
            msg = await client.send_file(chat_id, media, caption=text, formatting_entities=ents, buttons=tele_buttons(btns) if btns else None)
        else:
            msg = await client.send_message(chat_id, text, formatting_entities=ents, buttons=tele_buttons(btns) if btns else None, link_preview=False)
        if not force:
            uset(chat_id, welcome_last=msg.id)
    except Exception as exc:
        log.warning("welcome send failed: %s", exc)
        await client.send_message(chat_id, f"welcome {first}")

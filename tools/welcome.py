"""Welcome message save + send."""

from __future__ import annotations

import logging
import re
import time

from telethon.tl.types import User

from config import CONFIG
from tools.store import DATA_DIR, DEFAULT_WELCOME, gset, uset
from tools.style import (
    FALLBACK,
    btn,
    botapi,
    dump_ents,
    ents_to_api,
    load_ents,
    markup_json,
    pe_icon,
    shift_saved_ents,
    tele_buttons,
    utf16_len,
)

log = logging.getLogger("mentionbot")
PLACE_RE = re.compile(
    r"[{\uFF5B]\s*(mention|username|first_name|name|id|title|chatname|chat_name|group)\s*[}\uFF5D]",
    re.I,
)
BTN_RE = re.compile(r"\[\s*([^\]]+?)\s*\]\(\s*(https?://[^\s)]+)\s*\)")
welcome_seen: dict[str, float] = {}

UPDATES_URL = CONFIG.get("updates_url") or CONFIG.get("support_url")
SUPPORT_URL = CONFIG.get("support_url")


def default_welcome_buttons():
    return [
        [btn("updates", url=UPDATES_URL, pe_name="updates")],
        [btn("support", url=SUPPORT_URL, pe_name="support")],
    ]


def has_custom_emoji(saved) -> bool:
    for item in saved or []:
        kind = item.get("t") if isinstance(item, dict) else None
        if kind == "emoji" and item.get("id"):
            return True
        if getattr(item, "document_id", None):
            return True
    return False


def extract_buttons_keep_ents(text: str, saved_ents):
    buttons = []
    ents = [dict(x) for x in (saved_ents or [])]
    while True:
        match = BTN_RE.search(text or "")
        if not match:
            break
        buttons.append({"text": match.group(1).strip(), "url": match.group(2).strip()})
        start16 = utf16_len(text[:match.start()])
        old16 = utf16_len(match.group(0))
        text = text[:match.start()] + text[match.end():]
        ents = shift_saved_ents(ents, start16, old16, 0)
    text = (text or "").replace(" | ", "\n").strip()
    return text, buttons, ents


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
            extra = {"t": "mention", "off": start16, "len": utf16_len(repl), "uid": int(user.id)}
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


def add_line_premium(text: str, ents, pe_name: str = "welcome_line"):
    if ents and hasattr(ents[0], "offset"):
        saved = dump_ents(ents)
    else:
        saved = [dict(x) for x in (ents or [])]
    starts = [0]
    for idx, ch in enumerate(text or ""):
        if ch == "\n":
            starts.append(idx + 1)
    n = len(starts) - 1
    icon = pe_icon(pe_name) or pe_icon("welcome")
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
        saved.append({"t": "emoji", "off": start16, "len": utf16_len(FALLBACK), "id": int(icon)})
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
    rows = []
    for item in (items or [])[:8]:
        if isinstance(item, dict) and item.get("url"):
            name = (item.get("text") or "link").strip().lower()
            pe = "updates" if "update" in name else "support" if "support" in name else "welcome"
            rows.append([btn(item.get("text") or "link", url=item["url"], pe_name=pe)])
    return rows or default_welcome_buttons()


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
    raw, extra_btns, raw_ents = extract_buttons_keep_ents(raw, s.get("welcome_entities") if custom else [])
    values = {"first_name": first, "username": uname, "id": str(user.id), "chatname": title or "group"}
    text, ents = fill_welcome(raw, raw_ents or [], values, user)
    if not has_custom_emoji(raw_ents):
        text, ents = add_line_premium(text, ents, "welcome_line" if not custom else "welcome")
    if s.get("cleanwelcome") and s.get("welcome_last") and not force:
        try:
            await client.delete_messages(chat_id, int(s["welcome_last"]))
        except Exception:
            pass
    saved_btns = s.get("welcome_buttons") or extra_btns
    btns = parse_welcome_buttons(saved_btns)
    media = s.get("welcome_media") or ""
    try:
        payload = {"chat_id": chat_id}
        api_ents = ents_to_api(ents)
        if media and str(media).startswith("http"):
            payload.update({
                "photo": media,
                "caption": text,
                "caption_entities": api_ents,
                "reply_markup": markup_json(btns),
            })
            result = await botapi("sendPhoto", payload)
        else:
            payload.update({
                "text": text,
                "entities": api_ents,
                "link_preview_options": {"is_disabled": True},
                "reply_markup": markup_json(btns),
            })
            result = await botapi("sendMessage", payload)
        if result.get("ok"):
            if not force:
                uset(chat_id, welcome_last=result["result"]["message_id"])
            return
        if media:
            msg = await client.send_file(chat_id, media, caption=text, formatting_entities=ents, buttons=tele_buttons(btns))
        else:
            msg = await client.send_message(chat_id, text, formatting_entities=ents, buttons=tele_buttons(btns), link_preview=False)
        if not force:
            uset(chat_id, welcome_last=msg.id)
    except Exception as exc:
        log.warning("welcome send failed: %s", exc)
        await client.send_message(chat_id, f"welcome {first}")

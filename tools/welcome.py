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
    return [[btn("updates", url=UPDATES_URL, pe_name="welcome_b1")]]


def _left(i: int) -> int:
    return pe_icon(f"welcome_l{(i % 8) + 1}") or pe_icon("welcome_line") or pe_icon("welcome")


def _right(i: int) -> int:
    return pe_icon(f"welcome_r{(i % 8) + 1}") or _left(i)


def _sep(n: int) -> int:
    return pe_icon(f"sep_{n}") or pe_icon("welcome_line") or pe_icon("welcome")


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


def _append_sep_rows(out: str, ents: list) -> str:
    for n in range(1, 9):
        off = utf16_len(out)
        out += FALLBACK
        ents.append({"t": "emoji", "off": off, "len": utf16_len(FALLBACK), "id": int(_sep(n))})
    return out + "\n"


def wrap_welcome(text: str, ents, add_right: bool = True):
    if ents and hasattr(ents[0], "offset"):
        saved = dump_ents(ents)
    else:
        saved = [dict(x) for x in (ents or [])]
    raw_lines = (text or "").split("\n")
    out = ""
    new_ents = []
    line_i = 0
    cursor = 0
    for raw in raw_lines:
        nxt = cursor + len(raw)
        if raw.strip():
            left = FALLBACK + " "
            right = (" " + FALLBACK) if add_right else ""
            chunk = left + raw + right
            base = utf16_len(out)
            new_ents.append({"t": "emoji", "off": base, "len": utf16_len(FALLBACK), "id": int(_left(line_i))})
            start16 = utf16_len(text[:cursor])
            end16 = utf16_len(text[:nxt])
            for item in saved:
                off = int(item.get("off", 0))
                if start16 <= off < end16:
                    cur = dict(item)
                    cur["off"] = off - start16 + base + utf16_len(left)
                    new_ents.append(cur)
            if add_right:
                new_ents.append({
                    "t": "emoji",
                    "off": base + utf16_len(left + raw + " "),
                    "len": utf16_len(FALLBACK),
                    "id": int(_right(line_i)),
                })
            out += chunk + "\n"
            out = _append_sep_rows(out, new_ents)
            line_i += 1
        cursor = nxt + 1
    return out.rstrip(), load_ents(new_ents)


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
    for i, item in enumerate((items or [])[:8]):
        if isinstance(item, dict) and item.get("url"):
            pe = f"welcome_b{min(i + 1, 4)}"
            name = (item.get("text") or "link").strip().lower()
            if "update" in name:
                pe = "welcome_b1"
            elif "support" in name:
                pe = "welcome_b2"
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
    text, ents = wrap_welcome(text, ents, add_right=not custom)
    if s.get("cleanwelcome") and s.get("welcome_last") and not force:
        try:
            await client.delete_messages(chat_id, int(s["welcome_last"]))
        except Exception:
            pass
    if custom and extra_btns:
        saved_btns = s.get("welcome_buttons") or extra_btns
        btns = parse_welcome_buttons(saved_btns)
    elif custom and s.get("welcome_buttons"):
        btns = parse_welcome_buttons(s.get("welcome_buttons"))
    else:
        btns = default_welcome_buttons()
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

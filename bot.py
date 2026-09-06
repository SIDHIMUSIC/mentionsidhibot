#!/usr/bin/env python3
"""Mention bot — start menus, tag system, welcome, security guard."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import re
import time
from pathlib import Path

from dotenv import load_dotenv
from telethon import Button, TelegramClient, events
from telethon.errors import FloodWaitError, UserNotParticipantError
from telethon.tl.functions.channels import EditBannedRequest, GetParticipantRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.types import (
    ChannelParticipantAdmin,
    ChannelParticipantCreator,
    ChatBannedRights,
    MessageEntityCustomEmoji,
    MessageEntityTextUrl,
    User,
)

from config import CONFIG

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("mentionbot")

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(CONFIG["owner_id"])
OWNER_URL = CONFIG["owner_url"]
SUPPORT_URL = CONFIG["support_url"]
MUSIC_BOT_URL = CONFIG["music_bot_url"]
UPDATES_URL = CONFIG.get("updates_url", SUPPORT_URL)
START_PHOTOS = list(CONFIG["start_photos"])
PREMIUM_EMOJI_IDS = list(CONFIG["premium_emoji_ids"])
FALLBACK = "✨"

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_FILE = DATA_DIR / "settings.json"

DEFAULTS = {
    "admin_only": True,
    "cooldown": 12,
    "batch": 5,
    "names": True,
    "delay": 2,
    "welcome": False,
    "welcome_text": "Welcome {name} ✨",
    "biolink": False,
    "nolinks": False,
    "noswear": False,
    "nophone": False,
    "nohashtag": False,
    "noforward": False,
    "nobotpromo": False,
    "longmode": False,
    "long_limit": 500,
    "nomedia": False,
    "editprotect": False,
    "anticheat": False,
    "approved": [],
    "warns": {},
}

SWEAR = {"mc", "bc", "bhosd", "madarchod", "behenchod", "chutiya", "gandu"}
PHONE_RE = re.compile(r"(?:\+?\d[\d\-\s()]{8,}\d)")
LINK_RE = re.compile(r"(https?://|t\.me/|www\.|\.com\b|\.in\b)", re.I)
PROMO_RE = re.compile(r"(t\.me/\w+|@\w*bot\b)", re.I)

SC = str.maketrans(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢ",
)


def sc(text: str) -> str:
    return (text or "").translate(SC)


def sty(text: str) -> str:
    return sc(text)

ME_NAME = "Bot"
ME_USERNAME = ""


def bot_name() -> str:
    return ME_NAME or "Bot"


def load_all() -> dict:
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save_all(payload: dict) -> None:
    SETTINGS_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


ALL = load_all()


def gset(chat_id: int) -> dict:
    merged = dict(DEFAULTS)
    merged.update(ALL.get(str(chat_id), {}))
    return merged


def uset(chat_id: int, **changes) -> dict:
    cur = gset(chat_id)
    cur.update(changes)
    ALL[str(chat_id)] = cur
    save_all(ALL)
    return cur


if not API_ID or not API_HASH or not BOT_TOKEN:
    raise SystemExit("Set API_ID, API_HASH and BOT_TOKEN")

client = TelegramClient("mentionbot", API_ID, API_HASH)
active_jobs: set[int] = set()
last_run: dict[int, float] = {}
last_start: dict[int, float] = {}
cancel_by: dict[int, tuple] = {}
stats = {"mentions_sent": 0, "jobs": 0}
AFK: dict[int, str] = {}
COUPLES: dict[str, dict] = {}


def utf16_len(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def emoji_id(i: int) -> int:
    return PREMIUM_EMOJI_IDS[i % len(PREMIUM_EMOJI_IDS)]


def rich(text: str, start: int = 0):
    """Small-caps text with a premium custom emoji on every line."""
    text = sc(text)
    out = ""
    ents = []
    n = start
    for i, line in enumerate(text.split("\n")):
        if i:
            out += "\n"
        off = utf16_len(out)
        out += FALLBACK
        ents.append(MessageEntityCustomEmoji(off, utf16_len(FALLBACK), emoji_id(n)))
        n += 1
        if line:
            out += " " + line
    return out, ents


async def say(target, text: str, buttons=None, reply_to=None):
    body, ents = rich(text)
    kwargs = {"formatting_entities": ents, "link_preview": False}
    if buttons is not None:
        kwargs["buttons"] = buttons
    if reply_to is not None:
        kwargs["reply_to"] = reply_to
    chat = getattr(target, "chat_id", target)
    if hasattr(target, "reply") and reply_to is None and buttons is None:
        try:
            return await target.reply(body, formatting_entities=ents, link_preview=False)
        except Exception:
            pass
    return await client.send_message(chat, body, **kwargs)


async def edit_say(event, text: str, buttons=None):
    body, ents = rich(text)
    try:
        return await event.edit(body, formatting_entities=ents, buttons=buttons)
    except Exception:
        return await say(event, text, buttons=buttons)


def mention_pack(header: str, users: list[User], show_name: bool, start: int):
    text = header + "\n\n"
    ents = []
    for idx, user in enumerate(users):
        name = (user.first_name or "member").replace("]", "").replace("[", "")
        if not show_name:
            name = "♡"
        if idx:
            text += " "
        off = utf16_len(text)
        text += name
        ents.append(MessageEntityTextUrl(off, utf16_len(name), f"tg://user?id={user.id}"))
        text += " "
        eo = utf16_len(text)
        text += FALLBACK
        ents.append(MessageEntityCustomEmoji(eo, utf16_len(FALLBACK), emoji_id(start + idx)))
    return text, ents


def start_caption() -> str:
    handle = f"@{ME_USERNAME}" if ME_USERNAME else bot_name()
    return (
        f"ɪᴛꜱ ᴍᴇ — {bot_name()}\n"
        f"{handle}\n\n"
        "ꜱᴍᴀʀᴛ ᴛᴀɢ ʙᴏᴛ ꜰᴏʀ ɢʀᴏᴜᴘꜱ\n"
        "ᴘʀᴇᴍɪᴜᴍ ᴛᴀɢ + ɢᴀᴍᴇꜱ + ɢᴜᴀʀᴅ\n"
        "ᴀᴅᴅ ɪɴ ɢʀᴏᴜᴘ · ᴍᴀᴋᴇ ᴀᴅᴍɪɴ · ᴜꜱᴇ /ᴜᴛᴀɢ"
    )


def help_home() -> str:
    return (
        "ʜᴇʟᴘ ᴄᴇɴᴛᴇʀ — ꜱᴇʟᴇᴄᴛ ᴄᴀᴛᴇɢᴏʀʏ\n\n"
        "ᴛᴀɢ ꜱʏꜱᴛᴇᴍ — ᴍᴇᴍʙᴇʀꜱ & ᴀᴅᴍɪɴꜱ ᴛᴀɢ\n"
        "ᴄᴏᴜᴘʟᴇꜱ — 24ʜ / ᴘᴇʀᴍ ᴄᴏᴜᴘʟᴇ ꜱᴇᴛ\n"
        "ɢᴀᴍᴇꜱ — ᴛʀᴜᴛʜ ᴅᴀʀᴇ ꜱᴘɪɴ ʟᴏᴠᴇ\n"
        "ᴜꜱᴇʀ ᴛᴏᴏʟꜱ — ɪᴅ ᴘɪɴɢ ᴀꜰᴋ ꜱᴛᴀᴛꜱ\n"
        "ᴡᴇʟᴄᴏᴍᴇ — ɴᴇᴡ ᴍᴇᴍʙᴇʀ ᴍꜱɢ ᴏɴ/ᴏꜰꜰ\n"
        "ꜱᴇᴛᴛɪɴɢꜱ — ɢʀᴏᴜᴘ ᴛᴀɢ ᴏᴘᴛɪᴏɴꜱ\n"
        "ꜱᴇᴄᴜʀɪᴛʏ ɢᴜᴀʀᴅ — 14 ᴘʀᴏᴛᴇᴄᴛ ᴍᴏᴅᴜʟᴇꜱ"
    )


def start_buttons():
    add_url = f"https://t.me/{ME_USERNAME}?startgroup=true" if ME_USERNAME else SUPPORT_URL
    return [
        [Button.url(sc("✦ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ"), add_url)],
        [
            Button.url(sc("✦ ᴏᴡɴᴇʀ"), OWNER_URL),
            Button.inline(sc("✦ ɢᴀᴍᴇ"), b"menu:games"),
        ],
        [Button.inline(sc("✦ ʜᴇʟᴘ & ᴄᴏᴍᴍᴀɴᴅꜱ"), b"menu:help")],
        [
            Button.url(sc("✦ ꜱᴜᴘᴘᴏʀᴛ"), SUPPORT_URL),
            Button.url(sc("✦ ᴜᴘᴅᴀᴛᴇꜱ"), UPDATES_URL),
        ],
        [Button.url(sc("✦ ᴍᴜꜱɪᴄ ʙᴏᴛ"), MUSIC_BOT_URL)],
    ]


def help_buttons():
    return [
        [
            Button.inline(sc("✦ ᴛᴀɢ ꜱʏꜱᴛᴇᴍ"), b"menu:tag"),
            Button.inline(sc("✦ ᴄᴏᴜᴘʟᴇꜱ"), b"menu:couples"),
        ],
        [
            Button.inline(sc("✦ ɢᴀᴍᴇꜱ"), b"menu:games"),
            Button.inline(sc("✦ ᴜꜱᴇʀ ᴛᴏᴏʟꜱ"), b"menu:tools"),
        ],
        [
            Button.inline(sc("✦ ᴡᴇʟᴄᴏᴍᴇ"), b"menu:welcome"),
            Button.inline(sc("✦ ꜱᴇᴛᴛɪɴɢꜱ"), b"menu:gset"),
        ],
        [Button.inline(sc("✦ ꜱᴇᴄᴜʀɪᴛʏ ɢᴜᴀʀᴅ"), b"menu:security")],
        [Button.inline(sc("✦ ʙᴀᴄᴋ ᴛᴏ ꜱᴛᴀʀᴛ"), b"menu:start")],
    ]


def guard_buttons():
    return [
        [Button.inline(sc("✦ ᴀɴᴛɪ-ᴄʜᴇᴀᴛᴇʀ"), b"sec:anticheat"), Button.inline(sc("✦ ᴀʙᴜꜱᴇ"), b"sec:abuse")],
        [Button.inline(sc("✦ ᴀᴘᴘʀᴏᴠᴀʟꜱ"), b"sec:approve"), Button.inline(sc("✦ ʙɪᴏᴍᴏᴅᴇ"), b"sec:biolink")],
        [Button.inline(sc("✦ ᴍꜱɢᴅᴇʟᴇᴛᴇ"), b"sec:msgdel"), Button.inline(sc("✦ ᴇᴅɪᴛ"), b"sec:edit")],
        [Button.inline(sc("✦ ʟɪɴᴋꜱ"), b"sec:links"), Button.inline(sc("✦ ʟᴏɴɢᴍᴏᴅᴇ"), b"sec:long")],
        [Button.inline(sc("✦ ᴍᴇᴅɪᴀ"), b"sec:media"), Button.inline(sc("✦ ʙᴏᴛᴘʀᴏᴍᴏ"), b"sec:promo")],
        [Button.inline(sc("✦ ꜰᴏʀᴡᴀʀᴅ"), b"sec:fwd"), Button.inline(sc("✦ ʜᴀꜱʜᴛᴀɢꜱ"), b"sec:hash")],
        [Button.inline(sc("✦ ᴘʜᴏɴᴇ"), b"sec:phone"), Button.inline(sc("✦ ᴍᴜᴛᴇ & ᴡᴀʀɴ"), b"sec:mute")],
        [Button.inline(sc("✦ ʙᴀᴄᴋ ᴛᴏ ʜᴇʟᴘ"), b"menu:help")],
    ]


def nav_row():
    return [[Button.inline(sc("✦ ʜᴇʟᴘ"), b"menu:help"), Button.inline(sc("✦ ꜱᴛᴀʀᴛ"), b"menu:start")]]


def back_help():
    return [[Button.inline(sc("✦ ꜱᴇᴄᴜʀɪᴛʏ"), b"menu:security"), Button.inline(sc("✦ ʜᴇʟᴘ"), b"menu:help")]]


def onoff(flag: bool) -> str:
    return sc("ᴏɴ") if flag else sc("ᴏꜰꜰ")


async def is_admin(chat, user_id: int) -> bool:
    if OWNER_ID and user_id == OWNER_ID:
        return True
    try:
        result = await client(GetParticipantRequest(chat, user_id))
    except (UserNotParticipantError, Exception):
        return False
    return isinstance(result.participant, (ChannelParticipantAdmin, ChannelParticipantCreator))


async def collect(chat, kind: str) -> list[User]:
    out: list[User] = []
    async for user in client.iter_participants(chat):
        if not isinstance(user, User) or user.deleted or user.is_self:
            continue
        if kind == "all" and user.bot:
            continue
        if kind == "admins":
            if user.bot:
                continue
            if not await is_admin(chat, user.id):
                continue
        if kind == "bots" and not user.bot:
            continue
        out.append(user)
    return out


async def run_mention(event, kind: str, extra: str, force_admin=None) -> None:
    if event.is_private:
        await say(event, "ᴛᴀɢ ᴄᴏᴍᴍᴀɴᴅ ꜱɪʀꜰ ɢʀᴏᴜᴘ ᴍᴇɪɴ ᴄʜᴀʟᴛɪ ʜᴀɪ · ʙᴏᴛ ᴋᴏ ɢʀᴏᴜᴘ ᴍᴇɪɴ ᴀᴅᴅ ᴋᴀʀᴏ")
        return
    chat = await event.get_chat()
    chat_id = event.chat_id
    sender = await event.get_sender()
    s = gset(chat_id)
    need = s["admin_only"] if force_admin is None else force_admin
    if need and not await is_admin(chat, sender.id):
        await say(event, "ꜱɪʀꜰ ᴀᴅᴍɪɴꜱ ᴛᴀɢ ᴄʜᴀʟᴀ ꜱᴀᴋᴛᴇ ʜᴀɪɴ")
        return
    wait = s["cooldown"] - (time.time() - last_run.get(chat_id, 0))
    if wait > 0 and chat_id not in active_jobs:
        await say(event, f"ᴄᴏᴏʟᴅᴏᴡɴ {int(wait)}ꜱ")
        return
    if chat_id in active_jobs:
        await say(event, "ᴘᴇʜʟᴇ ꜱᴇ ᴛᴀɢ ᴄʜᴀʟ ʀᴀʜᴀ ʜᴀɪ · /ᴄᴀɴᴄᴇʟ")
        return
    active_jobs.add(chat_id)
    stats["jobs"] += 1
    last_run[chat_id] = time.time()
    try:
        members = await collect(chat, kind)
    except Exception as exc:
        active_jobs.discard(chat_id)
        await say(event, f"ᴍᴇᴍʙᴇʀꜱ ɴᴀʜɪ ᴍɪʟᴇ · ʙᴏᴛ ᴋᴏ ᴀᴅᴍɪɴ ʙᴀɴᴀᴏ · {type(exc).__name__}")
        return
    if not members:
        active_jobs.discard(chat_id)
        await say(event, "ᴋᴏɪ ᴍᴇᴍʙᴇʀ ɴᴀʜɪ ᴍɪʟᴀ")
        return
    header = extra.strip() if extra.strip() else sc(f"{bot_name()} — ꜱᴀʙ ʏᴀʜᴀɴ ᴀᴀᴏ")
    status = await say(event, f"ᴛᴀɢ ꜱᴛᴀʀᴛ · {len(members)} · /ᴄᴀɴᴄᴇʟ")
    sent = 0
    batch = max(3, min(8, int(s["batch"])))
    try:
        for i in range(0, len(members), batch):
            if chat_id not in active_jobs:
                who = cancel_by.get(chat_id)
                if who:
                    await mention_cancel(chat_id, who[0], who[1])
                else:
                    await say(event, "ᴛᴀɢ ᴄᴀɴᴄᴇʟ")
                return
            body, ents = mention_pack(header, members[i : i + batch], s["names"], i)
            try:
                await client.send_message(chat_id, body, formatting_entities=ents, link_preview=False)
            except FloodWaitError as fl:
                await asyncio.sleep(fl.seconds + 1)
                await client.send_message(chat_id, body, formatting_entities=ents, link_preview=False)
            sent += len(members[i : i + batch])
            stats["mentions_sent"] += len(members[i : i + batch])
            await asyncio.sleep(float(s.get("delay", 2)))
    finally:
        active_jobs.discard(chat_id)
    await say(event, f"ᴅᴏɴᴇ · {sent}/{len(members)} ᴍᴇɴᴛɪᴏɴ")


async def mention_cancel(chat_id: int, user_id: int, name: str) -> None:
    label = sc("ᴄᴀɴᴄᴇʟ ʙʏ ")
    text = label + name
    ents = [
        MessageEntityCustomEmoji(0, utf16_len(FALLBACK), emoji_id(0)),
    ]
    # rebuild with premium + mention
    text = FALLBACK + " " + label
    ents = [MessageEntityCustomEmoji(0, utf16_len(FALLBACK), emoji_id(0))]
    off = utf16_len(text)
    text += name
    ents.append(MessageEntityTextUrl(off, utf16_len(name), f"tg://user?id={user_id}"))
    await client.send_message(chat_id, text, formatting_entities=ents, link_preview=False)


async def send_start(event, force: bool = False):
    cid = event.chat_id
    now = time.time()
    if not force and now - last_start.get(cid, 0) < 2:
        return
    last_start[cid] = now
    photo = random.choice(START_PHOTOS) if START_PHOTOS else None
    cap, ents = rich(start_caption())
    if photo:
        try:
            await client.send_file(
                cid,
                photo,
                caption=cap,
                formatting_entities=ents,
                buttons=start_buttons(),
            )
            return
        except Exception as exc:
            log.warning("start photo: %s", exc)
    await client.send_message(cid, cap, formatting_entities=ents, buttons=start_buttons())


def extra_from(event) -> str:
    raw = event.raw_text or ""
    bits = raw.split(maxsplit=1)
    if len(bits) > 1 and not bits[1].startswith("@"):
        return bits[1]
    return ""


SEC_PAGES = {
    "sec:anticheat": "ᴀɴᴛɪ-ᴄʜᴇᴀᴛᴇʀ\n\nꜱᴘᴀᴍ / ᴄʜᴇᴀᴛ ᴍᴇꜱꜱᴀɢᴇ ᴅᴇʟᴇᴛᴇ\n/anticheat on\n/anticheat off",
    "sec:abuse": "ᴀʙᴜꜱᴇ ꜰɪʟᴛᴇʀ\n\nɢᴀʟɪ-ɢᴀʟᴏᴄʜ ᴅᴇʟᴇᴛᴇ\n/noswear on\n/noswear off",
    "sec:approve": "ᴀᴘᴘʀᴏᴠᴀʟꜱ\n\nᴀᴘᴘʀᴏᴠᴇᴅ ᴜꜱᴇʀ ꜰɪʟᴛᴇʀ ꜱᴇ ꜰʀᴇᴇ\n/approve reply\n/unapprove reply",
    "sec:biolink": "ʙɪᴏᴍᴏᴅᴇ\n\nʙɪᴏ ᴍᴇɪɴ ʟɪɴᴋ ʜᴏ ᴛᴏ ᴍꜱɢ ᴅᴇʟᴇᴛᴇ\n/biolink on\n/biolink off",
    "sec:msgdel": "ᴍꜱɢᴅᴇʟᴇᴛᴇ\n\n/nolinks /noswear /nophone\n/nohashtag /noforward /nobotpromo\n/longmode /nomedia",
    "sec:edit": "ᴇᴅɪᴛ ᴘʀᴏᴛᴇᴄᴛ\n\nᴇᴅɪᴛᴇᴅ ᴍꜱɢ ᴡᴀᴛᴄʜ\n/editprotect on\n/editprotect off",
    "sec:links": "ʟɪɴᴋꜱ\n\nᴜʀʟ ʙʟᴏᴄᴋ\n/nolinks on\n/nolinks off",
    "sec:long": "ʟᴏɴɢᴍᴏᴅᴇ\n\nʟᴏɴɢ ꜱᴘᴀᴍ ʙʟᴏᴄᴋ\n/longmode on\n/longmode off\n/longmode 500",
    "sec:media": "ᴍᴇᴅɪᴀ\n\nᴘʜᴏᴛᴏ/ᴠɪᴅᴇᴏ ʙʟᴏᴄᴋ\n/nomedia on\n/nomedia off",
    "sec:promo": "ʙᴏᴛᴘʀᴏᴍᴏ\n\nʙᴏᴛ ᴀᴅꜱ ʙʟᴏᴄᴋ\n/nobotpromo on\n/nobotpromo off",
    "sec:fwd": "ꜰᴏʀᴡᴀʀᴅ\n\nꜰᴏʀᴡᴀʀᴅᴇᴅ ᴍꜱɢ ʙʟᴏᴄᴋ\n/noforward on\n/noforward off",
    "sec:hash": "ʜᴀꜱʜᴛᴀɢꜱ\n\n#ᴛᴀɢ ꜱᴘᴀᴍ ʙʟᴏᴄᴋ\n/nohashtag on\n/nohashtag off",
    "sec:phone": "ᴘʜᴏɴᴇ\n\nɴᴜᴍʙᴇʀ ʙʟᴏᴄᴋ\n/nophone on\n/nophone off",
    "sec:mute": "ᴍᴜᴛᴇ & ᴡᴀʀɴ\n\n/warn reply\n/unwarn reply\n3 ᴡᴀʀɴ = ᴍᴜᴛᴇ",
}


@client.on(events.NewMessage(pattern=r"^/(start)(@\w+)?"))
async def start_h(event):
    await send_start(event, force=True)


@client.on(events.NewMessage(pattern=r"^/(help)(@\w+)?"))
async def help_h(event):
    photo = random.choice(START_PHOTOS) if START_PHOTOS else None
    cap, ents = rich(help_home())
    if photo:
        try:
            await client.send_file(event.chat_id, photo, caption=cap, formatting_entities=ents, buttons=help_buttons())
            return
        except Exception:
            pass
    await client.send_message(event.chat_id, cap, formatting_entities=ents, buttons=help_buttons())


@client.on(events.CallbackQuery)
async def clicks(event):
    data = event.data.decode() if event.data else ""
    pages = {
        "menu:help": (help_home(), help_buttons()),
        "menu:tag": (
            "ᴛᴀɢ ꜱʏꜱᴛᴇᴍ\n\n"
            "/utag /tagall /everyone @all\n"
            "ꜱᴀʙ ᴍᴇᴍʙᴇʀꜱ ᴛᴀɢ · ᴀᴅᴍɪɴ ᴏɴʟʏ · ʙᴏᴛꜱ ꜱᴋɪᴘ\n\n"
            "/atag /admins @admins\n"
            "ꜱɪʀꜰ ᴀᴅᴍɪɴꜱ ᴛᴀɢ · ʀᴇᴘᴏʀᴛ ɴᴀʜɪ\n\n"
            "/bots ʟɪꜱᴛ ᴏɴʟʏ\n"
            "/cancel ᴜꜱᴇʀ ᴍᴇɴᴛɪᴏɴ ᴋᴇ ꜱᴀᴛʜ ꜱᴛᴏᴘ\n"
            "/speed turbo|fast|normal|slow",
            nav_row(),
        ),
        "menu:couples": (
            "ᴄᴏᴜᴘʟᴇꜱ\n\n"
            "/couple reply · 24ʜ ᴄᴏᴜᴘʟᴇ\n"
            "/pcouple reply · ᴘᴇʀᴍ\n"
            "/mycouple · ᴄᴜʀʀᴇɴᴛ\n"
            "/breakup · ᴛᴏᴅᴏ\n"
            "/flirt · ᴄᴜᴛᴇ ʟɪɴᴇ",
            nav_row(),
        ),
        "menu:games": (
            "ɢᴀᴍᴇꜱ\n\n"
            "/truth · ʀᴀɴᴅᴏᴍ ᴛʀᴜᴛʜ\n"
            "/dare · ʀᴀɴᴅᴏᴍ ᴅᴀʀᴇ\n"
            "/tod · ᴛʀᴜᴛʜ ᴏʀ ᴅᴀʀᴇ\n"
            "/spin · ꜱᴜʀᴘʀɪꜱᴇ\n"
            "/love · % ᴍᴇᴛᴇʀ\n"
            "/kiss_marry_kill · 3 ᴍᴇᴍʙᴇʀꜱ",
            nav_row(),
        ),
        "menu:tools": (
            "ᴜꜱᴇʀ ᴛᴏᴏʟꜱ\n\n"
            "/id · ᴜꜱᴇʀ ɪᴅ\n"
            "/ping · ꜱᴘᴇᴇᴅ\n"
            "/afk · ᴀᴡᴀʏ\n"
            "/user_stats · ꜱᴛᴀᴛꜱ",
            nav_row(),
        ),
        "menu:welcome": (
            "ᴡᴇʟᴄᴏᴍᴇ\n\n"
            "/welcome on · ɴᴇᴡ ᴍᴇᴍʙᴇʀ ᴍꜱɢ\n"
            "/welcome off · ʙᴀɴᴅ\n"
            "/setwelcome text · {name} ʟɪᴋʜᴏ",
            [
                [Button.inline(sc("✦ ᴡᴇʟᴄᴏᴍᴇ ᴏɴ"), b"do:welcome_on"), Button.inline(sc("✦ ᴡᴇʟᴄᴏᴍᴇ ᴏꜰꜰ"), b"do:welcome_off")],
                *nav_row(),
            ],
        ),
        "menu:gset": (
            "ɢʀᴏᴜᴘ ꜱᴇᴛᴛɪɴɢꜱ\n\n"
            "/settings · ꜱᴀʀɪ ꜰʟᴀɢꜱ\n"
            "/settings admin_only on|off\n"
            "/settings cooldown 12\n"
            "/settings batch 5\n"
            "/speed 2\n"
            "/welcome on|off",
            nav_row(),
        ),
        "menu:security": (
            "ꜱᴇᴄᴜʀɪᴛʏ ɢᴜᴀʀᴅ\n\n"
            "ʜᴀʀ ᴍᴏᴅᴜʟᴇ ᴋᴀ ᴅᴇꜱᴄʀɪᴘᴛɪᴏɴ ʙᴜᴛᴛᴏɴ ᴋᴇ ᴀɴᴅᴀʀ\n"
            "ᴀᴅᴍɪɴ + ʙᴏᴛ ᴀᴅᴍɪɴ ᴢᴀʀᴏᴏʀɪ",
            guard_buttons(),
        ),
    }
    await event.answer()
    if data == "menu:start":
        await send_start(event, force=True)
        return
    if data == "do:welcome_on":
        if not event.is_private:
            uset(event.chat_id, welcome=True)
        await edit_say(event, "ᴡᴇʟᴄᴏᴍᴇ ᴏɴ", pages["menu:welcome"][1])
        return
    if data == "do:welcome_off":
        if not event.is_private:
            uset(event.chat_id, welcome=False)
        await edit_say(event, "ᴡᴇʟᴄᴏᴍᴇ ᴏꜰꜰ", pages["menu:welcome"][1])
        return
    if data in pages:
        await edit_say(event, pages[data][0], pages[data][1])
        return
    if data in SEC_PAGES:
        await edit_say(event, SEC_PAGES[data], back_help())


@client.on(events.NewMessage(pattern=r"^/(utag|tagall|everyone|all|mention)(@\w+)?"))
async def tag_all(event):
    extra = extra_from(event)
    if not extra and event.is_reply:
        r = await event.get_reply_message()
        extra = (r.raw_text if r else "") or extra
    await run_mention(event, "all", extra)


@client.on(events.NewMessage(pattern=r"^/(atag|admins|admin)(@\w+)?"))
async def tag_admins(event):
    await run_mention(event, "admins", extra_from(event) or "Admins needed", force_admin=False)


@client.on(events.NewMessage(pattern=r"^/(bots)(@\w+)?"))
async def bots_list(event):
    if event.is_private:
        await event.reply("Group mein `/bots` use karo.")
        return
    chat = await event.get_chat()
    bots = await collect(chat, "bots")
    title = getattr(chat, "title", "group")
    if not bots:
        await event.reply("Koi extra bot nahi mila.")
        return
    lines = [f"**BOT LIST — {title}**\n", "🤖 BOTS"]
    for i, b in enumerate(bots):
        name = f"@{b.username}" if b.username else (b.first_name or str(b.id))
        lines.append(("└" if i == len(bots) - 1 else "├") + " " + name)
    lines.append(f"\n**TOTAL NUMBER OF BOTS: {len(bots)}**")
    await event.reply("\n".join(lines))


@client.on(events.NewMessage(pattern=r"^/(cancel|stop)(@\w+)?"))
async def cancel(event):
    if event.is_private:
        return
    sender = await event.get_sender()
    name = sender.first_name or sender.username or str(sender.id)
    cancel_by[event.chat_id] = (sender.id, name)
    running = event.chat_id in active_jobs
    active_jobs.discard(event.chat_id)
    await mention_cancel(event.chat_id, sender.id, name)
    if not running:
        await say(event, "ᴋᴏɪ ᴛᴀɢ ᴄʜᴀʟ ɴᴀʜɪ ʀᴀʜᴀ")


@client.on(events.NewMessage(pattern=r"^/(ping)(@\w+)?"))
async def ping(event):
    t0 = time.perf_counter()
    msg = await event.reply("pong...")
    await msg.edit(f"pong `{(time.perf_counter() - t0) * 1000:.0f}ms`")


@client.on(events.NewMessage(pattern=r"^/(id)(@\w+)?"))
async def idc(event):
    if event.is_reply:
        u = await (await event.get_reply_message()).get_sender()
        await event.reply(f"ID: `{u.id}`\n{u.first_name}")
        return
    u = await event.get_sender()
    await event.reply(f"Your ID: `{u.id}`")


@client.on(events.NewMessage(pattern=r"^/(speed)(@\w+)?"))
async def speed(event):
    if event.is_private:
        return
    sender = await event.get_sender()
    if not await is_admin(await event.get_chat(), sender.id):
        return
    parts = [p for p in (event.raw_text or "").split() if not p.startswith("@")]
    presets = {"turbo": 1, "fast": 2, "normal": 3, "slow": 5, "reset": 2}
    if len(parts) == 1:
        await event.reply(f"Speed `{gset(event.chat_id).get('delay', 2)}s`")
        return
    val = parts[1].lower()
    delay = presets.get(val)
    if delay is None:
        try:
            delay = max(1, min(10, int(val)))
        except ValueError:
            await event.reply("`/speed 2`")
            return
    uset(event.chat_id, delay=delay)
    await event.reply(f"Speed `{delay}s`")


@client.on(events.NewMessage(pattern=r"^/(welcome)(@\w+)?"))
async def welcome_cmd(event):
    if event.is_private:
        await event.reply("Welcome group mein on/off hota hai.")
        return
    sender = await event.get_sender()
    if not await is_admin(await event.get_chat(), sender.id):
        await event.reply("Admin only.")
        return
    parts = [p for p in (event.raw_text or "").split() if not p.startswith("@")]
    if len(parts) == 1:
        await event.reply(f"Welcome {onoff(gset(event.chat_id)['welcome'])}")
        return
    on = parts[1].lower() in {"on", "true", "1"}
    uset(event.chat_id, welcome=on)
    await event.reply("Welcome " + onoff(on))


@client.on(events.NewMessage(pattern=r"^/(setwelcome)(@\w+)?"))
async def setwelcome(event):
    if event.is_private:
        return
    sender = await event.get_sender()
    if not await is_admin(await event.get_chat(), sender.id):
        return
    parts = (event.raw_text or "").split(maxsplit=1)
    if len(parts) < 2:
        await event.reply("`/setwelcome Welcome {name}`")
        return
    uset(event.chat_id, welcome_text=parts[1], welcome=True)
    await event.reply("Welcome text save. Welcome ON.")


TOGGLE_CMDS = {
    "biolink": "biolink",
    "nolinks": "nolinks",
    "noswear": "noswear",
    "nophone": "nophone",
    "nohashtag": "nohashtag",
    "noforward": "noforward",
    "nobotpromo": "nobotpromo",
    "longmode": "longmode",
    "nomedia": "nomedia",
    "editprotect": "editprotect",
    "anticheat": "anticheat",
}


@client.on(events.NewMessage(pattern=r"^/(biolink|nolinks|noswear|nophone|nohashtag|noforward|nobotpromo|longmode|nomedia|editprotect|anticheat)(@\w+)?"))
async def toggles(event):
    if event.is_private:
        await event.reply("Ye guard group mein chalta hai.")
        return
    sender = await event.get_sender()
    if not await is_admin(await event.get_chat(), sender.id):
        await event.reply("Admin only.")
        return
    cmd = (event.raw_text or "").split()[0].lstrip("/").split("@")[0].lower()
    key = TOGGLE_CMDS[cmd]
    parts = [p for p in (event.raw_text or "").split() if not p.startswith("@")]
    s = gset(event.chat_id)
    if len(parts) == 1:
        await event.reply(f"{cmd} {onoff(bool(s.get(key)))}")
        return
    if cmd == "longmode" and parts[1].isdigit():
        uset(event.chat_id, long_limit=int(parts[1]), longmode=True)
        await event.reply(f"longmode ON limit `{parts[1]}`")
        return
    flag = parts[1].lower() in {"on", "true", "1"}
    uset(event.chat_id, **{key: flag})
    await event.reply(f"{cmd} {onoff(flag)}")


@client.on(events.NewMessage(pattern=r"^/(settings)(@\w+)?"))
async def settings(event):
    if event.is_private:
        await event.reply("Settings group mein.")
        return
    s = gset(event.chat_id)
    parts = [p for p in (event.raw_text or "").split() if not p.startswith("@")]
    if len(parts) == 1:
        await event.reply(
            "⚙ GROUP SETTINGS\n"
            f"admin_only `{s['admin_only']}`\n"
            f"cooldown `{s['cooldown']}`\n"
            f"batch `{s['batch']}` delay `{s['delay']}`\n"
            f"welcome {onoff(s['welcome'])}\n"
            f"biolink {onoff(s['biolink'])} links {onoff(s['nolinks'])}\n"
            f"phone {onoff(s['nophone'])} hash {onoff(s['nohashtag'])}\n"
            f"forward {onoff(s['noforward'])} promo {onoff(s['nobotpromo'])}\n"
            f"long {onoff(s['longmode'])} media {onoff(s['nomedia'])}"
        )
        return
    sender = await event.get_sender()
    if not await is_admin(await event.get_chat(), sender.id):
        return
    if len(parts) < 3:
        return
    key, val = parts[1].lower(), parts[2].lower()
    if key == "admin_only":
        uset(event.chat_id, admin_only=val in {"on", "true", "1"})
    elif key == "cooldown":
        uset(event.chat_id, cooldown=max(5, min(300, int(val))))
    elif key == "batch":
        uset(event.chat_id, batch=max(3, min(8, int(val))))
    await event.reply("Updated.")


@client.on(events.NewMessage(pattern=r"^/(approve|unapprove)(@\w+)?"))
async def approve(event):
    if event.is_private or not event.is_reply:
        return
    sender = await event.get_sender()
    if not await is_admin(await event.get_chat(), sender.id):
        return
    target = await (await event.get_reply_message()).get_sender()
    s = gset(event.chat_id)
    approved = list(s.get("approved") or [])
    cmd = (event.raw_text or "").split()[0]
    if "unapprove" in cmd:
        approved = [x for x in approved if x != target.id]
        uset(event.chat_id, approved=approved)
        await event.reply("Unapproved.")
        return
    if target.id not in approved:
        approved.append(target.id)
    uset(event.chat_id, approved=approved)
    await event.reply("Approved.")


@client.on(events.NewMessage(pattern=r"^/(warn|unwarn)(@\w+)?"))
async def warn(event):
    if event.is_private or not event.is_reply:
        return
    sender = await event.get_sender()
    chat = await event.get_chat()
    if not await is_admin(chat, sender.id):
        return
    target = await (await event.get_reply_message()).get_sender()
    s = gset(event.chat_id)
    warns = dict(s.get("warns") or {})
    key = str(target.id)
    cmd = (event.raw_text or "").split()[0]
    if "unwarn" in cmd:
        warns[key] = max(0, int(warns.get(key, 0)) - 1)
        uset(event.chat_id, warns=warns)
        await event.reply(f"Warns: {warns[key]}")
        return
    warns[key] = int(warns.get(key, 0)) + 1
    uset(event.chat_id, warns=warns)
    await event.reply(f"Warn {warns[key]}/3")
    if warns[key] >= 3:
        try:
            await client(
                EditBannedRequest(
                    chat,
                    target.id,
                    ChatBannedRights(until_date=None, send_messages=True),
                )
            )
            await event.reply("3 warns — muted.")
        except Exception as exc:
            await event.reply(f"Mute fail: `{type(exc).__name__}`")


@client.on(events.ChatAction)
async def joined(event):
    if not (event.user_joined or event.user_added):
        return
    s = gset(event.chat_id)
    if not s.get("welcome"):
        return
    user = await event.get_user()
    if not user or user.bot:
        return
    text = (s.get("welcome_text") or "Welcome {name}").replace("{name}", user.first_name or "member")
    await event.reply(text)


@client.on(events.NewMessage(pattern=r"^/(truth|dare|tod|spin|love|flirt)(@\w+)?"))
async def fun(event):
    cmd = (event.raw_text or "").split()[0].lstrip("/").split("@")[0].lower()
    if cmd == "love":
        await event.reply(f"❤ Love meter: **{random.randint(1, 100)}%**")
        return
    if cmd == "flirt":
        await event.reply(random.choice(["Wifi nahi, connection tumse hai.", "Notification tumhara wait karta hoon."]))
        return
    await event.reply(random.choice(["Truth: last lie kab?", "Dare: stylish GM likho.", "Spin: Lucky!"]))


@client.on(events.NewMessage(pattern=r"^/(couple|pcouple|mycouple|breakup)(@\w+)?"))
async def couple(event):
    cmd = (event.raw_text or "").split()[0].lstrip("/").split("@")[0].lower()
    if cmd == "mycouple":
        pair = COUPLES.get(str(event.chat_id))
        await event.reply(f"{pair['an']} ♥ {pair['bn']}" if pair else "No couple.")
        return
    if cmd == "breakup":
        COUPLES.pop(str(event.chat_id), None)
        await event.reply("Breakup.")
        return
    if event.is_private or not event.is_reply:
        await event.reply("Reply karke `/couple`")
        return
    a = await event.get_sender()
    b = await (await event.get_reply_message()).get_sender()
    COUPLES[str(event.chat_id)] = {"an": a.first_name, "bn": b.first_name}
    await event.reply(f"{a.first_name} ♥ {b.first_name}")


@client.on(events.NewMessage(incoming=True))
async def incoming(event):
    if event.is_private or not event.raw_text:
        return
    text = event.raw_text.strip()
    low = text.lower()
    first = low.split(maxsplit=1)[0]
    extra = text.split(maxsplit=1)[1] if len(text.split(maxsplit=1)) > 1 else ""
    if first in {"@all", "#all", "@everyone", "#everyone"}:
        await run_mention(event, "all", extra)
        return
    if first in {"@admins", "#admins", "@admin"}:
        await run_mention(event, "admins", extra or "Admins needed", force_admin=False)
        return
    if low.startswith("/"):
        return
    sender = await event.get_sender()
    if not sender or sender.bot:
        return
    if await is_admin(await event.get_chat(), sender.id):
        return
    s = gset(event.chat_id)
    if sender.id in (s.get("approved") or []):
        return
    reason = None
    if s.get("nophone") and PHONE_RE.search(text):
        reason = "phone"
    elif s.get("nolinks") and LINK_RE.search(text):
        reason = "link"
    elif s.get("nohashtag") and "#" in text:
        reason = "hashtag"
    elif s.get("noforward") and event.fwd_from:
        reason = "forward"
    elif s.get("nobotpromo") and PROMO_RE.search(text):
        reason = "botpromo"
    elif s.get("noswear") and any(w in low for w in SWEAR):
        reason = "abuse"
    elif s.get("longmode") and len(text) > int(s.get("long_limit") or 500):
        reason = "long"
    elif s.get("anticheat") and text.count("t.me/") > 1:
        reason = "cheat"
    elif s.get("biolink"):
        try:
            full = await client(GetFullUserRequest(sender))
            about = getattr(full.full_user, "about", "") or ""
            if LINK_RE.search(about):
                reason = "biolink"
        except Exception:
            pass
    if reason:
        try:
            await event.delete()
        except Exception:
            pass


@client.on(events.NewMessage(incoming=True, func=lambda e: bool(e.media) and not e.is_private))
async def media_filter(event):
    s = gset(event.chat_id)
    if not s.get("nomedia"):
        return
    sender = await event.get_sender()
    if not sender or sender.bot:
        return
    if await is_admin(await event.get_chat(), sender.id):
        return
    try:
        await event.delete()
    except Exception:
        pass


async def main() -> None:
    global ME_NAME, ME_USERNAME
    await client.start(bot_token=BOT_TOKEN)
    me = await client.get_me()
    ME_NAME = (me.first_name or me.username or "Bot").strip()
    ME_USERNAME = me.username or ""
    log.info("Started %s @%s", ME_NAME, ME_USERNAME)
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())

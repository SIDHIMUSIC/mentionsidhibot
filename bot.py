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

_MAP = str.maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
    "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇",
)

def sty(text: str) -> str:
    return text.translate(_MAP)

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
stats = {"mentions_sent": 0, "jobs": 0}
AFK: dict[int, str] = {}
COUPLES: dict[str, dict] = {}


def utf16_len(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def emoji_id(i: int) -> int:
    return PREMIUM_EMOJI_IDS[i % len(PREMIUM_EMOJI_IDS)]


def decorate(text: str, n: int = 3):
    """Prefix a few custom premium emojis onto plain text."""
    out = ""
    ents = []
    for i in range(min(n, len(PREMIUM_EMOJI_IDS))):
        off = utf16_len(out)
        out += FALLBACK
        ents.append(MessageEntityCustomEmoji(off, utf16_len(FALLBACK), emoji_id(i)))
        out += " "
    out += text
    return out, ents


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
        f"♡ It's Me — {bot_name()}\n"
        f"{handle}\n\n"
        "📌 A Smart Tag-Bot\n"
        "△ Fun Conversations\n"
        "Works in Groups & Private\n"
        "Keeps Chats Active + Fun\n"
        "⚠ Premium Tag System\n"
        "⚡ Stylish & Smooth\n"
        "Games · Fun Tools · Guard"
    )


def help_home() -> str:
    return (
        "📚 HELP CENTER — SELECT CATEGORY\n\n"
        "Choose a section below:\n\n"
        "△ TAG SYSTEM — tag members & admins\n"
        "Couple system — set couples\n"
        "Games — fun games\n"
        "User tools — utilities\n"
        "Welcome — welcome on/off\n"
        "⚠ Security Guard — group protection\n"
        "⚙ Group Settings — toggles"
    )


def start_buttons():
    add_url = f"https://t.me/{ME_USERNAME}?startgroup=true" if ME_USERNAME else SUPPORT_URL
    return [
        [Button.url(f"♡ {sty('ADD ME TO YOUR GROUP')}", add_url)],
        [
            Button.url(f"👑 {sty('OWNER')}", OWNER_URL),
            Button.inline(f"🎮 {sty('GAME')}", b"menu:games"),
        ],
        [Button.inline(f"△ {sty('HELP & COMMANDS')}", b"menu:help")],
        [
            Button.url(f"💬 {sty('SUPPORT')}", SUPPORT_URL),
            Button.url(f"⚡ {sty('UPDATES')}", UPDATES_URL),
        ],
        [Button.url(f"🎵 {sty('MUSIC BOT')}", MUSIC_BOT_URL)],
    ]


def help_buttons():
    return [
        [
            Button.inline(f"△ {sty('TAG SYSTEM')}", b"menu:tag"),
            Button.inline(f"🔥 {sty('COUPLES')}", b"menu:couples"),
        ],
        [
            Button.inline(f"🎮 {sty('GAMES')}", b"menu:games"),
            Button.inline(f"✨ {sty('USER TOOLS')}", b"menu:tools"),
        ],
        [
            Button.inline(f"👋 {sty('WELCOME')}", b"menu:welcome"),
            Button.inline(f"⚙ {sty('SETTINGS')}", b"menu:gset"),
        ],
        [Button.inline(f"⚠ {sty('SECURITY GUARD')}", b"menu:security")],
        [Button.inline(f"🏠 {sty('BACK TO START')}", b"menu:start")],
    ]


def guard_buttons():
    return [
        [
            Button.inline("⚠ 🚫 ANTI-CHEATER", b"sec:anticheat"),
            Button.inline("⚠ 🚫 ABUSE", b"sec:abuse"),
        ],
        [
            Button.inline("🔵 ✅ APPROVALS", b"sec:approve"),
            Button.inline("⚡ 🙈 BIOMODE", b"sec:biolink"),
        ],
        [
            Button.inline("🚨 🗑 MSGDELETE", b"sec:msgdel"),
            Button.inline("🔮 ✏️ EDIT", b"sec:edit"),
        ],
        [
            Button.inline("🔗 LINKS", b"sec:links"),
            Button.inline("⚡ 📜 LONGMODE", b"sec:long"),
        ],
        [
            Button.inline("📌 📸 MEDIA", b"sec:media"),
            Button.inline("🐹 📢 BOTPROMO", b"sec:promo"),
        ],
        [
            Button.inline("🔥 ↩️ FORWARD", b"sec:fwd"),
            Button.inline("⚡ # HASHTAGS", b"sec:hash"),
        ],
        [
            Button.inline("🔵 📞 PHONE", b"sec:phone"),
            Button.inline("🚨 📣 MUTE & WARN", b"sec:mute"),
        ],
        [Button.inline("🔵 ⬅️ BACK TO HELP", b"menu:help")],
    ]


def back_help():
    return [
        [
            Button.inline(f"⚠ {sty('SECURITY')}", b"menu:security"),
            Button.inline(f"📚 {sty('HELP')}", b"menu:help"),
        ]
    ]


def onoff(flag: bool) -> str:
    return "ON ✅" if flag else "OFF ❌"


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
        await event.reply("Ye tag command **group** mein chalti hai. Bot ko group mein add karke `/utag` do.")
        return
    chat = await event.get_chat()
    chat_id = event.chat_id
    sender = await event.get_sender()
    s = gset(chat_id)
    need = s["admin_only"] if force_admin is None else force_admin
    if need and not await is_admin(chat, sender.id):
        await event.reply("Sirf admins tag chala sakte hain.")
        return
    wait = s["cooldown"] - (time.time() - last_run.get(chat_id, 0))
    if wait > 0 and chat_id not in active_jobs:
        await event.reply(f"Cooldown `{int(wait)}s`")
        return
    if chat_id in active_jobs:
        await event.reply("Pehle se tag chal raha hai. `/cancel`")
        return
    active_jobs.add(chat_id)
    stats["jobs"] += 1
    last_run[chat_id] = time.time()
    try:
        members = await collect(chat, kind)
    except Exception as exc:
        active_jobs.discard(chat_id)
        await event.reply(f"Members nahi mile. Bot ko admin banao.\n`{type(exc).__name__}`")
        return
    if not members:
        active_jobs.discard(chat_id)
        await event.reply("Koi member nahi mila.")
        return
    header = extra.strip() if extra.strip() else f"{bot_name()} — sab yahan aao"
    status = await event.reply(f"Tag start — **{len(members)}**\n`/cancel`")
    sent = 0
    batch = max(3, min(8, int(s["batch"])))
    try:
        for i in range(0, len(members), batch):
            if chat_id not in active_jobs:
                await event.reply("Tag cancel.")
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
    try:
        await status.edit(f"Done ✨ {sent}/{len(members)}")
    except Exception:
        await event.reply(f"Done ✨ {sent}/{len(members)}")


async def send_start(event):
    cid = event.chat_id
    now = time.time()
    if now - last_start.get(cid, 0) < 2:
        return
    last_start[cid] = now
    photo = random.choice(START_PHOTOS) if START_PHOTOS else None
    if photo:
        try:
            await client.send_file(
                cid,
                photo,
                caption=start_caption(),
                buttons=start_buttons(),
                reply_to=getattr(event, "id", None),
            )
            return
        except Exception as exc:
            log.warning("start photo: %s", exc)
    await event.reply(start_caption(), buttons=start_buttons())


def extra_from(event) -> str:
    raw = event.raw_text or ""
    bits = raw.split(maxsplit=1)
    if len(bits) > 1 and not bits[1].startswith("@"):
        return bits[1]
    return ""


SEC_PAGES = {
    "sec:anticheat": (
        "⚠ ANTI-CHEATER\n\n"
        "Spam / cheat-style messages delete.\n\n"
        "`/anticheat on`\n`/anticheat off`"
    ),
    "sec:abuse": (
        "⚠ ABUSE\n\n"
        "Gali-galoch delete.\n\n"
        "`/noswear on`\n`/noswear off`"
    ),
    "sec:approve": (
        "🔵 APPROVALS\n\n"
        "Approved users filters se free.\n\n"
        "`/approve` reply\n`/unapprove` reply"
    ),
    "sec:biolink": (
        "⚡ BIOMODE / BioLink Guard\n\n"
        "Bio mein link ho to message delete.\n\n"
        "`/biolink on`\n`/biolink off`"
    ),
    "sec:msgdel": (
        "🚨 MSGDELETE\n\n"
        "Filters:\n"
        "`/nolinks on|off`\n"
        "`/noswear on|off`\n"
        "`/nophone on|off`\n"
        "`/nohashtag on|off`\n"
        "`/noforward on|off`\n"
        "`/nobotpromo on|off`\n"
        "`/longmode on|off`\n"
        "`/nomedia on|off`"
    ),
    "sec:edit": (
        "🔮 EDIT PROTECT\n\n"
        "Edited messages watch.\n\n"
        "`/editprotect on`\n`/editprotect off`"
    ),
    "sec:links": (
        "🔗 LINKS\n\n"
        "`/nolinks on` block URLs\n"
        "`/nolinks off`"
    ),
    "sec:long": (
        "📜 LONGMODE\n\n"
        "`/longmode on`\n"
        "`/longmode off`\n"
        "`/longmode 500`"
    ),
    "sec:media": (
        "📌 MEDIA\n\n"
        "`/nomedia on` photos/videos block\n"
        "`/nomedia off`"
    ),
    "sec:promo": (
        "📢 BOTPROMO\n\n"
        "`/nobotpromo on`\n`/nobotpromo off`"
    ),
    "sec:fwd": (
        "↩️ FORWARD\n\n"
        "`/noforward on`\n`/noforward off`"
    ),
    "sec:hash": (
        "# HASHTAGS\n\n"
        "`/nohashtag on`\n`/nohashtag off`"
    ),
    "sec:phone": (
        "📞 PHONE\n\n"
        "`/nophone on`\n`/nophone off`\n`/nophone`"
    ),
    "sec:mute": (
        "📣 MUTE & WARN\n\n"
        "`/warn` reply\n"
        "`/unwarn` reply\n"
        "3 warns = mute"
    ),
}


@client.on(events.NewMessage(pattern=r"^/(start)(@\w+)?"))
async def start_h(event):
    await send_start(event)


@client.on(events.NewMessage(pattern=r"^/(help)(@\w+)?"))
async def help_h(event):
    await event.reply(help_home(), buttons=help_buttons())


@client.on(events.CallbackQuery)
async def clicks(event):
    data = event.data.decode() if event.data else ""
    pages = {
        "menu:help": (help_home(), help_buttons()),
        "menu:tag": (
            "△ TAG SYSTEM\n\n"
            "`/utag` `/tagall` `/everyone` `@all`\n"
            "All members — admin only\n\n"
            "`/atag` `/admins` `@admins`\n"
            "Sirf admins tag — group mein kaam karta hai\n\n"
            "`/bots` list only, mention nahi\n"
            "`/cancel` `/speed turbo|fast|normal|slow`",
            [
                [Button.inline(f"🏠 {sty('HELP')}", b"menu:help"), Button.inline(f"✨ {sty('START')}", b"menu:start")]
            ],
        ),
        "menu:couples": (
            "🔥 COUPLES\n\n`/couple` reply\n`/breakup`\n`/mycouple`\n`/flirt`",
            help_buttons()[:1] + back_help(),
        ),
        "menu:games": (
            "🎮 GAMES\n\n`/truth` `/dare` `/tod` `/spin` `/love` `/kiss_marry_kill`",
            [
                [Button.inline(f"🏠 {sty('HELP')}", b"menu:help"), Button.inline(f"✨ {sty('START')}", b"menu:start")]
            ],
        ),
        "menu:tools": (
            "✨ USER TOOLS\n\n`/id` `/ping` `/afk` `/user_stats`",
            [
                [Button.inline(f"🏠 {sty('HELP')}", b"menu:help"), Button.inline(f"✨ {sty('START')}", b"menu:start")]
            ],
        ),
        "menu:welcome": (
            "👋 WELCOME\n\n"
            "`/welcome on` — naya member aaye to msg\n"
            "`/welcome off`\n"
            "`/setwelcome text` — custom text, `{name}` use karo",
            [
                [Button.inline(f"🟢 {sty('WELCOME ON')}", b"do:welcome_on"), Button.inline(f"🔴 {sty('WELCOME OFF')}", b"do:welcome_off")],
                [Button.inline(f"🏠 {sty('HELP')}", b"menu:help")],
            ],
        ),
        "menu:gset": (
            "⚙ GROUP SETTINGS\n\n"
            "`/settings` dekho\n"
            "`/settings admin_only on|off`\n"
            "`/settings cooldown 12`\n"
            "`/settings batch 5`\n"
            "`/speed 2`\n"
            "`/welcome on|off`",
            [
                [Button.inline(f"⚠ {sty('SECURITY')}", b"menu:security")],
                [Button.inline(f"🏠 {sty('HELP')}", b"menu:help")],
            ],
        ),
        "menu:security": (
            "⚠ SECURITY GUARD\n\nSelect a module:",
            guard_buttons(),
        ),
    }
    await event.answer()
    if data == "menu:start":
        await send_start(event)
        return
    if data == "do:welcome_on":
        if event.is_private:
            await event.reply("Welcome group mein on hota hai.")
            return
        uset(event.chat_id, welcome=True)
        try:
            await event.edit("Welcome ON ✅", buttons=pages["menu:welcome"][1])
        except Exception:
            await event.reply("Welcome ON ✅")
        return
    if data == "do:welcome_off":
        if not event.is_private:
            uset(event.chat_id, welcome=False)
        try:
            await event.edit("Welcome OFF ❌", buttons=pages["menu:welcome"][1])
        except Exception:
            await event.reply("Welcome OFF ❌")
        return
    if data in pages:
        text, btns = pages[data]
        try:
            await event.edit(text, buttons=btns)
        except Exception:
            await event.reply(text, buttons=btns)
        return
    if data in SEC_PAGES:
        try:
            await event.edit(SEC_PAGES[data], buttons=back_help())
        except Exception:
            await event.reply(SEC_PAGES[data], buttons=back_help())


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
    active_jobs.discard(event.chat_id)
    await event.reply("Tag stop.")


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

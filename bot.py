#!/usr/bin/env python3
"""Telegram mention-all bot. Display name comes from the live BotFather account."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import time
from pathlib import Path

from aiohttp import web
from dotenv import load_dotenv
from telethon import Button, TelegramClient, events
from telethon.errors import FloodWaitError, UserNotParticipantError
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.tl.types import (
    ChannelParticipantAdmin,
    ChannelParticipantCreator,
    MessageEntityCustomEmoji,
    MessageEntityTextUrl,
    User,
)

from config import CONFIG

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("mentionbot")

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
PORT = int(os.getenv("PORT", "0") or 0)

OWNER_ID = int(CONFIG["owner_id"])
OWNER_URL = CONFIG["owner_url"]
SUPPORT_URL = CONFIG["support_url"]
MUSIC_BOT_URL = CONFIG["music_bot_url"]
START_PHOTOS = list(CONFIG["start_photos"])
PREMIUM_EMOJI_IDS = list(CONFIG["premium_emoji_ids"])
FALLBACK_EMOJI = "\u2728"

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_FILE = DATA_DIR / "settings.json"

DEFAULT_SETTINGS = {
    "admin_only": True,
    "cooldown": 45,
    "batch": 5,
    "names": True,
}

ME_NAME = "Bot"
ME_USERNAME = ""


def bot_name() -> str:
    return ME_NAME or "Bot"


def load_all_settings() -> dict:
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            log.warning("settings.json corrupt, starting fresh")
    return {}


def save_all_settings(payload: dict) -> None:
    SETTINGS_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


ALL_SETTINGS = load_all_settings()


def chat_settings(chat_id: int) -> dict:
    key = str(chat_id)
    merged = dict(DEFAULT_SETTINGS)
    merged.update(ALL_SETTINGS.get(key, {}))
    return merged


def update_chat_settings(chat_id: int, **changes) -> dict:
    key = str(chat_id)
    current = chat_settings(chat_id)
    current.update(changes)
    ALL_SETTINGS[key] = current
    save_all_settings(ALL_SETTINGS)
    return current


if not API_ID or not API_HASH or not BOT_TOKEN:
    raise SystemExit("Set API_ID, API_HASH and BOT_TOKEN in env / .env")

client = TelegramClient("mentionbot", API_ID, API_HASH)

active_jobs: set[int] = set()
last_run: dict[int, float] = {}
stats = {"mentions_sent": 0, "jobs": 0}


def utf16_len(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def pick_emoji_id(index: int) -> int:
    return PREMIUM_EMOJI_IDS[index % len(PREMIUM_EMOJI_IDS)]


def build_mention_message(header: str, users: list[User], show_name: bool, start_index: int):
    text = header + "\n\n"
    entities = []
    for idx, user in enumerate(users):
        name = (user.first_name or "member").replace("]", "").replace("[", "")
        if not show_name:
            name = "\u2661"
        if idx:
            text += " "
        name_offset = utf16_len(text)
        text += name
        entities.append(
            MessageEntityTextUrl(
                offset=name_offset,
                length=utf16_len(name),
                url=f"tg://user?id={user.id}",
            )
        )
        text += " "
        emoji_offset = utf16_len(text)
        text += FALLBACK_EMOJI
        entities.append(
            MessageEntityCustomEmoji(
                offset=emoji_offset,
                length=utf16_len(FALLBACK_EMOJI),
                document_id=pick_emoji_id(start_index + idx),
            )
        )
    return text, entities


def start_caption() -> str:
    handle = f"@{ME_USERNAME}" if ME_USERNAME else bot_name()
    return (
        f"\u2728 Welcome to {bot_name()} \u2728\n"
        f"{handle}\n\n"
        "Group ke saare members ko stylish mention\n"
        "`/all`  `/tagall`  `/everyone`\n"
        "Group mein `@all` ya `#all` bhi chalega\n"
        "`/admins`  `/bots`  `/cancel`\n\n"
        "Bot ko group **admin** banao, phir tag shuru.\n"
        "Help: `/help`"
    )


def help_text() -> str:
    return (
        f"**{bot_name()} commands**\n\n"
        "`/all` `/tagall` `/everyone` `[text]`\n"
        "`@all` `#all` `@everyone`\n"
        "`/admins` \u2014 sirf admins\n"
        "`/bots` \u2014 group bots\n"
        "`/cancel` `/stop`\n"
        "`/settings` \u2014 admin_only / cooldown / batch / names\n"
        "`/stats` `/ping` `/help`\n\n"
        "Har member ke baad premium emoji lagta hai."
    )


def start_buttons():
    add_url = (
        f"https://t.me/{ME_USERNAME}?startgroup=true" if ME_USERNAME else SUPPORT_URL
    )
    return [
        [
            Button.url("\U0001f451 OWNER", OWNER_URL),
            Button.url("\U0001f4ac SUPPORT", SUPPORT_URL),
        ],
        [
            Button.url("\U0001f3b5 MUSIC BOT", MUSIC_BOT_URL),
            Button.url("\u2795 ADD GROUP", add_url),
        ],
    ]


async def is_admin(chat, user_id: int) -> bool:
    if OWNER_ID and user_id == OWNER_ID:
        return True
    try:
        result = await client(GetParticipantRequest(chat, user_id))
    except UserNotParticipantError:
        return False
    except Exception as exc:
        log.debug("admin check failed: %s", exc)
        return False
    return isinstance(
        result.participant,
        (ChannelParticipantAdmin, ChannelParticipantCreator),
    )


async def collect_members(chat, kind: str) -> list[User]:
    members: list[User] = []
    async for user in client.iter_participants(chat):
        if not isinstance(user, User):
            continue
        if user.deleted or user.is_self:
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
        members.append(user)
    return members


async def run_mention(event, kind: str, extra_text: str) -> None:
    chat = await event.get_chat()
    chat_id = event.chat_id
    sender = await event.get_sender()
    if event.is_private:
        await event.reply("Ye command sirf **group** mein chalti hai.")
        return

    settings = chat_settings(chat_id)
    if settings["admin_only"] and not await is_admin(chat, sender.id):
        await event.reply("Sirf **admins** mention chala sakte hain.")
        return

    wait = settings["cooldown"] - (time.time() - last_run.get(chat_id, 0))
    if wait > 0 and chat_id not in active_jobs:
        await event.reply(f"Cooldown `{int(wait)}s` bacha hai.")
        return

    if chat_id in active_jobs:
        await event.reply("Pehle se mention chal raha hai. `/cancel`")
        return

    active_jobs.add(chat_id)
    stats["jobs"] += 1
    last_run[chat_id] = time.time()
    batch = max(3, min(8, int(settings["batch"])))
    show_name = bool(settings["names"])

    try:
        members = await collect_members(chat, kind)
    except Exception as exc:
        active_jobs.discard(chat_id)
        log.exception("member fetch failed")
        await event.reply(
            "Members nahi mile. Bot ko **admin** banao.\n"
            f"`{type(exc).__name__}`"
        )
        return

    if not members:
        active_jobs.discard(chat_id)
        await event.reply("Koi eligible member nahi mila.")
        return

    header = extra_text.strip() if extra_text.strip() else f"{bot_name()} \u2014 sab yahan aao"
    status = await event.reply(
        f"Mention start \u2014 **{len(members)}**  \u00b7  batch `{batch}`\nrokne ke liye `/cancel`"
    )

    sent = 0
    try:
        for i in range(0, len(members), batch):
            if chat_id not in active_jobs:
                await event.reply("Mention **cancel** ho gaya.")
                return
            chunk = members[i : i + batch]
            body, entities = build_mention_message(header, chunk, show_name, i)
            try:
                await client.send_message(
                    chat_id, body, formatting_entities=entities, link_preview=False
                )
                sent += len(chunk)
                stats["mentions_sent"] += len(chunk)
            except FloodWaitError as flood:
                log.warning("FloodWait %ss", flood.seconds)
                await asyncio.sleep(flood.seconds + 1)
                await client.send_message(
                    chat_id, body, formatting_entities=entities, link_preview=False
                )
                sent += len(chunk)
            await asyncio.sleep(1.6)
    finally:
        active_jobs.discard(chat_id)

    done = f"Done  {sent}/{len(members)} mention ho gaye."
    try:
        await status.edit(done)
    except Exception:
        await event.reply(done)


@client.on(events.NewMessage(pattern=r"^/(start)(@\w+)?"))
async def start_handler(event):
    caption = start_caption()
    buttons = start_buttons()
    photo = random.choice(START_PHOTOS) if START_PHOTOS else None
    if photo:
        try:
            await client.send_file(
                event.chat_id,
                photo,
                caption=caption,
                buttons=buttons,
                reply_to=event.id,
            )
            return
        except Exception as exc:
            log.warning("start photo failed: %s", exc)
    await event.reply(caption, buttons=buttons)


@client.on(events.NewMessage(pattern=r"^/(help)(@\w+)?"))
async def help_handler(event):
    await event.reply(help_text(), buttons=start_buttons())


@client.on(events.NewMessage(pattern=r"^/(ping)(@\w+)?"))
async def ping_handler(event):
    t0 = time.perf_counter()
    msg = await event.reply("pong...")
    ms = (time.perf_counter() - t0) * 1000
    await msg.edit(f"pong `{ms:.0f}ms`")


@client.on(events.NewMessage(pattern=r"^/(stats)(@\w+)?"))
async def stats_handler(event):
    settings = chat_settings(event.chat_id)
    running = "haan" if event.chat_id in active_jobs else "nahi"
    await event.reply(
        f"**{bot_name()} stats**\n"
        f"Jobs: `{stats['jobs']}`\n"
        f"Mentions: `{stats['mentions_sent']}`\n"
        f"Running: `{running}`\n"
        f"admin_only: `{settings['admin_only']}`\n"
        f"cooldown: `{settings['cooldown']}s`\n"
        f"batch: `{settings['batch']}`"
    )


@client.on(events.NewMessage(pattern=r"^/(cancel|stop)(@\w+)?"))
async def cancel_handler(event):
    if event.is_private:
        return
    chat = await event.get_chat()
    sender = await event.get_sender()
    if chat_settings(event.chat_id)["admin_only"] and not await is_admin(chat, sender.id):
        await event.reply("Cancel ke liye admin hona chahiye.")
        return
    if event.chat_id in active_jobs:
        active_jobs.discard(event.chat_id)
        await event.reply("Mention stop.")
    else:
        await event.reply("Koi mention chal nahi raha.")


@client.on(events.NewMessage(pattern=r"^/(settings)(@\w+)?"))
async def settings_handler(event):
    if event.is_private:
        await event.reply("Settings group mein change hoti hain.")
        return
    chat = await event.get_chat()
    sender = await event.get_sender()
    parts = (event.raw_text or "").split()
    if len(parts) == 1 or (len(parts) == 2 and parts[1].startswith("@")):
        s = chat_settings(event.chat_id)
        await event.reply(
            "**Group settings**\n"
            f"`admin_only` = `{s['admin_only']}`\n"
            f"`cooldown` = `{s['cooldown']}`\n"
            f"`batch` = `{s['batch']}`\n"
            f"`names` = `{s['names']}`\n\n"
            "`/settings admin_only on`\n"
            "`/settings cooldown 60`\n"
            "`/settings batch 5`\n"
            "`/settings names off`"
        )
        return

    if not await is_admin(chat, sender.id):
        await event.reply("Settings sirf admin badal sakta hai.")
        return

    args = [p for p in parts[1:] if not p.startswith("@")]
    if len(args) < 2:
        await event.reply("Usage: `/settings admin_only on`")
        return

    key, value = args[0].lower(), args[1].lower()
    if key == "admin_only":
        if value not in {"on", "off", "true", "false", "1", "0"}:
            await event.reply("`on` ya `off` likho.")
            return
        s = update_chat_settings(event.chat_id, admin_only=value in {"on", "true", "1"})
    elif key == "cooldown":
        try:
            seconds = max(10, min(600, int(value)))
        except ValueError:
            await event.reply("Cooldown seconds mein do, jaise `60`.")
            return
        s = update_chat_settings(event.chat_id, cooldown=seconds)
    elif key == "batch":
        try:
            batch = max(3, min(8, int(value)))
        except ValueError:
            await event.reply("Batch 3 se 8 ke beech rakho.")
            return
        s = update_chat_settings(event.chat_id, batch=batch)
    elif key == "names":
        if value not in {"on", "off", "true", "false", "1", "0"}:
            await event.reply("`on` ya `off` likho.")
            return
        s = update_chat_settings(event.chat_id, names=value in {"on", "true", "1"})
    else:
        await event.reply("Unknown key. `admin_only`, `cooldown`, `batch`, `names`.")
        return

    await event.reply(
        "Updated\n"
        f"`admin_only={s['admin_only']}` `cooldown={s['cooldown']}` "
        f"`batch={s['batch']}` `names={s['names']}`"
    )


MENTION_CMD = r"^/(all|tagall|everyone|mention)(@\w+)?"


@client.on(events.NewMessage(pattern=MENTION_CMD))
async def mention_cmd(event):
    extra = ""
    raw = event.raw_text or ""
    bits = raw.split(maxsplit=1)
    if len(bits) > 1 and not bits[1].startswith("@"):
        extra = bits[1]
    elif event.is_reply:
        reply = await event.get_reply_message()
        if reply and reply.raw_text:
            extra = reply.raw_text
    await run_mention(event, "all", extra)


@client.on(events.NewMessage(pattern=r"^/(admins|admin)(@\w+)?"))
async def admins_cmd(event):
    extra = ""
    raw = event.raw_text or ""
    bits = raw.split(maxsplit=1)
    if len(bits) > 1 and not bits[1].startswith("@"):
        extra = bits[1]
    await run_mention(event, "admins", extra or "Admins needed")


@client.on(events.NewMessage(pattern=r"^/(bots)(@\w+)?"))
async def bots_cmd(event):
    await run_mention(event, "bots", "Group bots")


@client.on(events.NewMessage(incoming=True))
async def text_triggers(event):
    if event.is_private or not event.raw_text:
        return
    text = event.raw_text.strip().lower()
    if text.startswith("/"):
        return
    triggers = {"@all", "#all", "@everyone", "#everyone"}
    first = text.split(maxsplit=1)[0]
    if first not in triggers and text not in triggers:
        return
    extra = ""
    parts = event.raw_text.split(maxsplit=1)
    if len(parts) > 1:
        extra = parts[1]
    await run_mention(event, "all", extra)


async def health(_request):
    return web.json_response(
        {
            "ok": True,
            "name": bot_name(),
            "username": ME_USERNAME,
            "active_jobs": len(active_jobs),
            "mentions_sent": stats["mentions_sent"],
        }
    )


async def start_health_server() -> web.AppRunner | None:
    if not PORT:
        log.info("PORT not set — health server skipped (worker mode)")
        return None
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    log.info("Health server on 0.0.0.0:%s", PORT)
    return runner


async def main() -> None:
    global ME_NAME, ME_USERNAME
    await client.start(bot_token=BOT_TOKEN)
    me = await client.get_me()
    ME_NAME = (me.first_name or me.username or "Bot").strip()
    ME_USERNAME = me.username or ""
    log.info("Started as %s (@%s)", ME_NAME, ME_USERNAME)
    runner = await start_health_server()
    try:
        await client.run_until_disconnected()
    finally:
        if runner:
            await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

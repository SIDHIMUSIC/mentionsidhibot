#!/usr/bin/env python3
"""MentionMayaBot — Telegram group mention bot."""

from __future__ import annotations

import asyncio
import json
import logging
import os
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
    User,
)

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("mentionmaya")

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_ID", "0") or 0)
PORT = int(os.getenv("PORT", "0") or 0)

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_FILE = DATA_DIR / "settings.json"

DEFAULT_SETTINGS = {
    "admin_only": True,
    "cooldown": 45,
    "batch": 5,
    "names": True,
}

HELP_TEXT = (
    "**MentionMayaBot** \U0001faf6\n\n"
    "Group ke sab logon ko tag karne wala bot.\n\n"
    "**Mention**\n"
    "`/all` `/tagall` `/everyone` `/mention` `[text]`\n"
    "Group mein `@all` `#all` `@everyone` bhi chalega.\n\n"
    "**Aur commands**\n"
    "`/admins` — sirf admins\n"
    "`/bots` — group bots\n"
    "`/cancel` `/stop` — mention band\n"
    "`/settings` — group options\n"
    "`/stats` `/ping` `/help`\n\n"
    "Bot ko group **admin** banana zaroori hai."
)

START_TEXT = (
    "Hey, main **MentionMayaBot** hoon \U0001f979\n\n"
    "Mujhe group mein add karo, admin banao, phir `/all` ya `@all` se "
    "saari team ko ek saath bulao.\n\n"
    "Help ke liye `/help`."
)


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

client = TelegramClient("mentionmaya", API_ID, API_HASH)

active_jobs: set[int] = set()
last_run: dict[int, float] = {}
stats = {"mentions_sent": 0, "jobs": 0}


async def is_admin(chat, user_id: int) -> bool:
    if OWNER_ID and user_id == OWNER_ID:
        return True
    try:
        result = await client(GetParticipantRequest(chat, user_id))
    except UserNotParticipantError:
        return False
    except Exception as exc:  # noqa: BLE001
        log.debug("admin check failed: %s", exc)
        return False
    return isinstance(
        result.participant,
        (ChannelParticipantAdmin, ChannelParticipantCreator),
    )


def mention_link(user: User, show_name: bool) -> str:
    name = (user.first_name or "member").replace("]", "").replace("[", "")
    if not show_name:
        name = "\u2022"
    return f"[{name}](tg://user?id={user.id})"


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
        await event.reply("Ye command sirf **group/channel** mein kaam karti hai.")
        return

    settings = chat_settings(chat_id)
    if settings["admin_only"] and not await is_admin(chat, sender.id):
        await event.reply("Sirf **admins** mention chala sakte hain. `/settings`")
        return

    wait = settings["cooldown"] - (time.time() - last_run.get(chat_id, 0))
    if wait > 0 and chat_id not in active_jobs:
        await event.reply(f"Thoda ruko — cooldown `{int(wait)}s` bacha hai.")
        return

    if chat_id in active_jobs:
        await event.reply("Is group mein mention pehle se chal raha hai. `/cancel`")
        return

    active_jobs.add(chat_id)
    stats["jobs"] += 1
    last_run[chat_id] = time.time()
    batch = max(3, min(8, int(settings["batch"])))
    show_name = bool(settings["names"])

    try:
        members = await collect_members(chat, kind)
    except Exception as exc:  # noqa: BLE001
        active_jobs.discard(chat_id)
        log.exception("member fetch failed")
        await event.reply(
            "Members nahi mil paaye. Bot ko **admin** banao aur dubara try karo.\n"
            f"`{type(exc).__name__}`"
        )
        return

    if not members:
        active_jobs.discard(chat_id)
        await event.reply("Koi eligible member nahi mila.")
        return

    header = extra_text.strip() if extra_text.strip() else "Maya bol rahi hai — sab yahan aao \U0001faf6"
    status = await event.reply(
        f"Mention start — **{len(members)}** log, batch `{batch}`. `/cancel` se rok sakte ho."
    )

    sent = 0
    try:
        for i in range(0, len(members), batch):
            if chat_id not in active_jobs:
                await event.reply("Mention **cancel** ho gaya.")
                return
            chunk = members[i : i + batch]
            body = header + "\n\n" + " ".join(mention_link(u, show_name) for u in chunk)
            try:
                await client.send_message(chat_id, body, link_preview=False)
                sent += len(chunk)
                stats["mentions_sent"] += len(chunk)
            except FloodWaitError as flood:
                log.warning("FloodWait %ss", flood.seconds)
                await asyncio.sleep(flood.seconds + 1)
                await client.send_message(chat_id, body, link_preview=False)
                sent += len(chunk)
            await asyncio.sleep(1.6)
    finally:
        active_jobs.discard(chat_id)

    try:
        await status.edit(f"Done \u2705  {sent}/{len(members)} mention ho gaye.")
    except Exception:  # noqa: BLE001
        await event.reply(f"Done \u2705  {sent}/{len(members)} mention ho gaye.")


@client.on(events.NewMessage(pattern=r"^/(start)(@\w+)?"))
async def start_handler(event):
    buttons = [
        [Button.url("BotFather", "https://t.me/BotFather")],
        [Button.url("Source", "https://github.com/SIDHIMUSIC/mentionmayabot")],
    ]
    await event.reply(START_TEXT, buttons=buttons)


@client.on(events.NewMessage(pattern=r"^/(help)(@\w+)?"))
async def help_handler(event):
    await event.reply(HELP_TEXT)


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
        "**Stats**\n"
        f"Jobs: `{stats['jobs']}`\n"
        f"Mentions sent: `{stats['mentions_sent']}`\n"
        f"Is group running: `{running}`\n"
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
        await event.reply("Mention stop kar diya.")
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
            "Change:\n"
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
        "Updated \u2705\n"
        f"`admin_only={s['admin_only']}` `cooldown={s['cooldown']}` "
        f"`batch={s['batch']}` `names={s['names']}`"
    )


MENTION_CMD = r"^/(all|tagall|everyone|mention|maya)(@\w+)?"


@client.on(events.NewMessage(pattern=MENTION_CMD))
async def mention_cmd(event):
    extra = ""
    raw = event.raw_text or ""
    bits = raw.split(maxsplit=1)
    if len(bits) > 1 and not bits[1].startswith(":") and not bits[1].startswith(":"):
        extra = bits[1] if not bits[1].startswith("@") else ""
        if bits[1].startswith("@") and event.is_reply:
            extra = ""
    if not extra and event.is_reply:
        reply = await event.get_reply_message()
        if reply and reply.raw_text:
            extra = reply.raw_text
    if len(bits) > 1 and not bits[1].startswith("@"):
        extra = bits[1]
    await run_mention(event, "all", extra)


@client.on(events.NewMessage(pattern=r"^/(admins|admin)(@\w+)?"))
async def admins_cmd(event):
    extra = ""
    raw = event.raw_text or ""
    bits = raw.split(maxsplit=1)
    if len(bits) > 1 and not bits[1].startswith("@"):
        extra = bits[1]
    await run_mention(event, "admins", extra or "Admins needed \U0001f6a8")


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
    triggers = {"@all", "#all", "@everyone", "#everyone", "@mentionmaya"}
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
            "bot": "mentionmayabot",
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
    await client.start(bot_token=BOT_TOKEN)
    me = await client.get_me()
    log.info("Bot started as @%s (%s)", me.username, me.id)
    runner = await start_health_server()
    try:
        await client.run_until_disconnected()
    finally:
        if runner:
            await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""Mention bot entry. Handlers live in tools/."""

from __future__ import annotations

import asyncio
import logging
import os

from dotenv import load_dotenv
from telethon import TelegramClient

from config import CONFIG
from tools import runtime
from tools.handlers import register

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("mentionbot")

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(CONFIG["owner_id"])
START_PHOTOS = list(CONFIG["start_photos"])

if not API_ID or not API_HASH or not BOT_TOKEN:
    raise SystemExit("Set API_ID, API_HASH and BOT_TOKEN")

client = TelegramClient("mentionbot", API_ID, API_HASH)
runtime.client = client
register(client, OWNER_ID, START_PHOTOS)


async def main() -> None:
    await client.start(bot_token=BOT_TOKEN)
    me = await client.get_me()
    runtime.ME_NAME = (me.first_name or me.username or "Bot").strip()
    runtime.ME_USERNAME = me.username or ""
    log.info("Started %s @%s", runtime.ME_NAME, runtime.ME_USERNAME)
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())

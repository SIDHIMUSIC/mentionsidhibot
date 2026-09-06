"""Owner stats + broadcast. Track users/groups. Auto welcome when bot joins."""

from __future__ import annotations

import asyncio

from telethon import events

from config import CONFIG
from tools.store import (
    all_chat_ids,
    all_user_ids,
    count_chats,
    count_users,
    touch_chat,
    touch_user,
    uset,
)
from tools.style import say

OWNER_ID = int(CONFIG["owner_id"])


def register_owner(client) -> None:
    @client.on(events.NewMessage)
    async def track(event):
        sender = await event.get_sender()
        if sender and getattr(sender, "id", None):
            touch_user(sender.id, sender.first_name or sender.username or "")
        if not event.is_private:
            chat = await event.get_chat()
            touch_chat(event.chat_id, getattr(chat, "title", "") or "")

    @client.on(events.ChatAction)
    async def bot_added(event):
        if not (event.user_added or event.user_joined):
            return
        me = await client.get_me()
        added = False
        users = event.users or []
        if event.user_id and event.user_id == me.id:
            added = True
        for user in users:
            if getattr(user, "id", None) == me.id:
                added = True
        if added:
            chat = await event.get_chat()
            uset(event.chat_id, welcome=True)
            touch_chat(event.chat_id, getattr(chat, "title", "") or "")
            try:
                await client.send_message(event.chat_id, "welcome auto on. /welcome off se band.")
            except Exception:
                pass
            return
        user = await event.get_user()
        if user and not user.bot:
            touch_user(user.id, user.first_name or "")

    @client.on(events.NewMessage(pattern=r"^/(stats|status)(@\w+)?"))
    async def stats_cmd(event):
        sender = await event.get_sender()
        if not sender or sender.id != OWNER_ID:
            return
        text = (
            "sᴛᴀᴛs\n\n"
            f"users {count_users()}\n"
            f"groups {count_chats()}"
        )
        await say(client, event, text)

    @client.on(events.NewMessage(pattern=r"^/(broadcast|gcast)(@\w+)?"))
    async def broadcast_cmd(event):
        sender = await event.get_sender()
        if not sender or sender.id != OWNER_ID:
            return
        text = ""
        raw = event.raw_text or ""
        parts = raw.split(maxsplit=1)
        if len(parts) > 1:
            text = parts[1]
        reply = await event.get_reply_message() if event.is_reply else None
        if not text and reply:
            text = reply.raw_text or reply.message or ""
        if not text.strip() and not (reply and reply.media):
            await say(client, event, "/broadcast text ya reply")
            return
        chats = all_chat_ids()
        users = all_user_ids()
        ok = 0
        fail = 0
        await say(client, event, f"broadcast start groups {len(chats)} users {len(users)}")
        targets = list(dict.fromkeys(chats + users))
        for cid in targets:
            try:
                if reply and reply.media and not text:
                    await client.send_file(cid, reply.media, caption=reply.message or "")
                else:
                    await client.send_message(cid, text)
                ok += 1
            except Exception:
                fail += 1
            await asyncio.sleep(0.05)
        await say(client, event, f"broadcast done ok {ok} fail {fail}")

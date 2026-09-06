"""All command handlers. Registered from bot.py."""
from __future__ import annotations

import asyncio
import logging
import random
import re
import time

from telethon import events
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

from tools import runtime
from tools.menus import (
    WELCOME_HELP, back_help, guard_buttons, help_buttons, help_home, nav_row,
    onoff, start_buttons, start_caption, welcome_buttons, welcome_status_text,
)
from tools.store import DEFAULT_WELCOME, gset, uset
from tools.style import (
    FALLBACK, botapi, dump_ents, edit_say, emoji_id, ents_to_api, markup_json,
    rich, say, sc, tele_buttons, utf16_len,
)
from tools.welcome import BTN_RE, grab_welcome_media, send_welcome, setwelcome_prefix

log = logging.getLogger("mentionbot")
OWNER_ID = 8170572505
START_PHOTOS = []
SWEAR = {"mc", "bc", "bhosd", "madarchod", "behenchod", "chutiya", "gandu"}
PHONE_RE = re.compile(r"(?:\+?\d[\d\-\s()]{8,}\d)")
LINK_RE = re.compile(r"(https?://|t\.me/|www\.|\.com\b|\.in\b)", re.I)
PROMO_RE = re.compile(r"(t\.me/\w+|@\w*bot\b)", re.I)
active_jobs: set[int] = set()
last_run: dict[int, float] = {}
last_start: dict[int, float] = {}
cancel_by: dict[int, tuple] = {}
stats = {"mentions_sent": 0, "jobs": 0}
COUPLES: dict[str, dict] = {}
TOGGLE_CMDS = {
    "biolink": "biolink", "nolinks": "nolinks", "noswear": "noswear", "nophone": "nophone",
    "nohashtag": "nohashtag", "noforward": "noforward", "nobotpromo": "nobotpromo",
    "longmode": "longmode", "nomedia": "nomedia", "editprotect": "editprotect", "anticheat": "anticheat",
}
SEC_PAGES = {
    "sec:anticheat": "anti-cheater\n/anticheat on|off",
    "sec:abuse": "abuse filter\n/noswear on|off",
    "sec:approve": "approvals\n/approve reply\n/unapprove reply",
    "sec:biolink": "biomode\n/biolink on|off",
    "sec:msgdel": "msgdelete\n/nolinks /noswear /nophone /nohashtag /noforward /nobotpromo /longmode /nomedia",
    "sec:edit": "edit protect\n/editprotect on|off",
    "sec:links": "links\n/nolinks on|off",
    "sec:long": "longmode\n/longmode on|off|500",
    "sec:media": "media\n/nomedia on|off",
    "sec:promo": "botpromo\n/nobotpromo on|off",
    "sec:fwd": "forward\n/noforward on|off",
    "sec:hash": "hashtags\n/nohashtag on|off",
    "sec:phone": "phone\n/nophone on|off",
    "sec:mute": "mute warn\n/warn reply\n/unwarn reply\n3 warn = mute",
}


def extra_from(event) -> str:
    raw = event.raw_text or ""
    bits = raw.split(maxsplit=1)
    if len(bits) > 1 and not bits[1].startswith("@"):
        return bits[1]
    return ""


def register(client, owner_id: int, start_photos: list) -> None:
    global OWNER_ID, START_PHOTOS
    OWNER_ID = owner_id
    START_PHOTOS = list(start_photos or [])
    runtime.client = client

    async def is_admin(chat, user_id: int) -> bool:
        if OWNER_ID and user_id == OWNER_ID:
            return True
        try:
            result = await client(GetParticipantRequest(chat, user_id))
        except Exception:
            return False
        return isinstance(result.participant, (ChannelParticipantAdmin, ChannelParticipantCreator))

    async def collect(chat, kind: str) -> list[User]:
        out: list[User] = []
        async for user in client.iter_participants(chat):
            if not isinstance(user, User) or user.deleted or user.is_self:
                continue
            if kind == "all" and user.bot:
                continue
            if kind == "admins" and (user.bot or not await is_admin(chat, user.id)):
                continue
            if kind == "bots" and not user.bot:
                continue
            out.append(user)
        return out

    def mention_pack(header: str, users: list[User], show_name: bool, start: int):
        text = header + "\n\n"
        ents = []
        for idx, user in enumerate(users):
            name = (user.first_name or "member").replace("]", "").replace("[", "")
            if not show_name:
                name = "*"
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

    async def mention_cancel(chat_id: int, user_id: int, name: str) -> None:
        text = FALLBACK + " " + sc("cancel by ")
        ents = [MessageEntityCustomEmoji(0, utf16_len(FALLBACK), emoji_id(0))]
        off = utf16_len(text)
        text += name
        ents.append(MessageEntityTextUrl(off, utf16_len(name), f"tg://user?id={user_id}"))
        await client.send_message(chat_id, text, formatting_entities=ents, link_preview=False)

    async def run_mention(event, kind: str, extra: str, force_admin=None) -> None:
        if event.is_private:
            await say(client, event, "tag command group mein chalti hai")
            return
        chat = await event.get_chat()
        chat_id = event.chat_id
        sender = await event.get_sender()
        s = gset(chat_id)
        need = s["admin_only"] if force_admin is None else force_admin
        if need and not await is_admin(chat, sender.id):
            await say(client, event, "sirf admins tag chala sakte hain")
            return
        wait = s["cooldown"] - (time.time() - last_run.get(chat_id, 0))
        if wait > 0 and chat_id not in active_jobs:
            await say(client, event, f"cooldown {int(wait)}s")
            return
        if chat_id in active_jobs:
            await say(client, event, "pehle se tag chal raha hai /cancel")
            return
        active_jobs.add(chat_id)
        stats["jobs"] += 1
        last_run[chat_id] = time.time()
        try:
            members = await collect(chat, kind)
        except Exception as exc:
            active_jobs.discard(chat_id)
            await say(client, event, f"members nahi mile bot ko admin banao {type(exc).__name__}")
            return
        if not members:
            active_jobs.discard(chat_id)
            await say(client, event, "koi member nahi mila")
            return
        header = extra.strip() if extra.strip() else sc(f"{runtime.bot_name()} - sab yahan aao")
        await say(client, event, f"tag start {len(members)} /cancel")
        sent = 0
        batch = max(3, min(8, int(s["batch"])))
        try:
            for i in range(0, len(members), batch):
                if chat_id not in active_jobs:
                    who = cancel_by.get(chat_id)
                    if who:
                        await mention_cancel(chat_id, who[0], who[1])
                    return
                body, ents = mention_pack(header, members[i:i + batch], s["names"], i)
                try:
                    await client.send_message(chat_id, body, formatting_entities=ents, link_preview=False)
                except FloodWaitError as fl:
                    await asyncio.sleep(fl.seconds + 1)
                    await client.send_message(chat_id, body, formatting_entities=ents, link_preview=False)
                sent += len(members[i:i + batch])
                stats["mentions_sent"] += len(members[i:i + batch])
                await asyncio.sleep(float(s.get("delay", 2)))
        finally:
            active_jobs.discard(chat_id)
        await say(client, event, f"done {sent}/{len(members)} mention")

    async def send_start(event, force: bool = False):
        cid = event.chat_id
        now = time.time()
        if not force and now - last_start.get(cid, 0) < 2:
            return
        last_start[cid] = now
        photo = random.choice(START_PHOTOS) if START_PHOTOS else None
        cap, ents = rich(start_caption())
        rows = start_buttons()
        if photo:
            result = await botapi("sendPhoto", {"chat_id": cid, "photo": photo, "caption": cap, "caption_entities": ents_to_api(ents), "reply_markup": markup_json(rows)})
            if result.get("ok"):
                return
        await botapi("sendMessage", {"chat_id": cid, "text": cap, "entities": ents_to_api(ents), "link_preview_options": {"is_disabled": True}, "reply_markup": markup_json(rows)})

    @client.on(events.NewMessage(pattern=r"^/(start)(@\w+)?"))
    async def start_h(event):
        await send_start(event, force=True)

    @client.on(events.NewMessage(pattern=r"^/(help)(@\w+)?"))
    async def help_h(event):
        cap, ents = rich(help_home())
        rows = help_buttons()
        photo = random.choice(START_PHOTOS) if START_PHOTOS else None
        if photo:
            result = await botapi("sendPhoto", {"chat_id": event.chat_id, "photo": photo, "caption": cap, "caption_entities": ents_to_api(ents), "reply_markup": markup_json(rows)})
            if result.get("ok"):
                return
        await botapi("sendMessage", {"chat_id": event.chat_id, "text": cap, "entities": ents_to_api(ents), "link_preview_options": {"is_disabled": True}, "reply_markup": markup_json(rows)})

    @client.on(events.CallbackQuery)
    async def clicks(event):
        data = event.data.decode() if event.data else ""
        pages = {
            "menu:help": (help_home(), help_buttons()),
            "menu:tag": ("tag system\n/utag /tagall /everyone @all\n/atag /admins @admins\n/bots list\n/cancel\n/speed turbo|fast|normal|slow", nav_row()),
            "menu:couples": ("couples\n/couple reply\n/pcouple reply\n/mycouple\n/breakup\n/flirt", nav_row()),
            "menu:games": ("games\n/truth /dare /tod /spin /love", nav_row()),
            "menu:tools": ("user tools\n/id /ping /afk", nav_row()),
            "menu:welcome": (WELCOME_HELP, welcome_buttons()),
            "menu:gset": ("group settings\n/settings\n/speed 2\n/welcome on|off", nav_row()),
            "menu:security": ("security guard\n14 modules. button dabao", guard_buttons()),
        }
        await event.answer()
        if data == "menu:start":
            await send_start(event, force=True)
            return
        flags = {"do:welcome_on": ("welcome", True), "do:welcome_off": ("welcome", False), "do:clean_on": ("cleanwelcome", True), "do:clean_off": ("cleanwelcome", False)}
        if data in flags and not event.is_private:
            key, val = flags[data]
            uset(event.chat_id, **{key: val})
            await edit_say(event, welcome_status_text(event.chat_id), welcome_buttons())
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
            reply = await event.get_reply_message()
            extra = (reply.raw_text if reply else "") or extra
        await run_mention(event, "all", extra)

    @client.on(events.NewMessage(pattern=r"^/(atag|admins|admin)(@\w+)?"))
    async def tag_admins(event):
        await run_mention(event, "admins", extra_from(event) or "Admins needed", force_admin=False)

    @client.on(events.NewMessage(pattern=r"^/(bots)(@\w+)?"))
    async def bots_list(event):
        if event.is_private:
            await event.reply("Group mein /bots use karo.")
            return
        bots = await collect(await event.get_chat(), "bots")
        title = getattr(await event.get_chat(), "title", "group")
        if not bots:
            await event.reply("Koi extra bot nahi mila.")
            return
        lines = [f"BOT LIST - {title}\n", "BOTS"]
        for i, bot in enumerate(bots):
            name = f"@{bot.username}" if bot.username else (bot.first_name or str(bot.id))
            lines.append(("L " if i == len(bots) - 1 else "+ ") + name)
        lines.append(f"\nTOTAL BOTS: {len(bots)}")
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
            await say(client, event, "koi tag nahi chal raha")

    @client.on(events.NewMessage(pattern=r"^/(ping)(@\w+)?"))
    async def ping(event):
        t0 = time.perf_counter()
        msg = await event.reply("pong...")
        await msg.edit(f"pong {(time.perf_counter() - t0) * 1000:.0f}ms")

    @client.on(events.NewMessage(pattern=r"^/(id)(@\w+)?"))
    async def idc(event):
        if event.is_reply:
            user = await (await event.get_reply_message()).get_sender()
            await event.reply(f"ID: {user.id}\n{user.first_name}")
            return
        user = await event.get_sender()
        await event.reply(f"Your ID: {user.id}")

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
            await event.reply(f"Speed {gset(event.chat_id).get('delay', 2)}s")
            return
        val = parts[1].lower()
        delay = presets.get(val)
        if delay is None:
            try:
                delay = max(1, min(10, int(val)))
            except ValueError:
                await event.reply("/speed 2")
                return
        uset(event.chat_id, delay=delay)
        await event.reply(f"Speed {delay}s")

    @client.on(events.NewMessage(pattern=r"^/(welcome)(@\w+)?"))
    async def welcome_cmd(event):
        if event.is_private:
            return
        sender = await event.get_sender()
        if not await is_admin(await event.get_chat(), sender.id):
            return
        parts = [p for p in (event.raw_text or "").split() if not p.startswith("@")]
        s = gset(event.chat_id)
        if len(parts) == 1:
            await say(client, event, f"welcome {onoff(s['welcome'])} clean {onoff(s.get('cleanwelcome'))}")
            return
        flag = parts[1].lower() in {"on", "true", "1"}
        uset(event.chat_id, welcome=flag)
        await say(client, event, "welcome " + onoff(flag))

    @client.on(events.NewMessage(pattern=r"^/(cleanwelcome)(@\w+)?"))
    async def cleanwelcome_cmd(event):
        if event.is_private:
            return
        sender = await event.get_sender()
        if not await is_admin(await event.get_chat(), sender.id):
            return
        parts = [p for p in (event.raw_text or "").split() if not p.startswith("@")]
        if len(parts) == 1:
            await say(client, event, "cleanwelcome " + onoff(gset(event.chat_id).get("cleanwelcome")))
            return
        flag = parts[1].lower() in {"on", "true", "1"}
        uset(event.chat_id, cleanwelcome=flag)
        await say(client, event, "cleanwelcome " + onoff(flag))

    @client.on(events.NewMessage(pattern=r"^/(setwelcome)(@\w+)?"))
    async def setwelcome(event):
        if event.is_private:
            return
        sender = await event.get_sender()
        if not await is_admin(await event.get_chat(), sender.id):
            return
        raw = event.raw_text or event.message.message or ""
        prefix = setwelcome_prefix(raw)
        text = raw[len(prefix):] if prefix else extra_from(event)
        saved_ents = dump_ents(event.message.entities, shift=utf16_len(prefix)) if text else []
        media = ""
        if event.is_reply:
            reply = await event.get_reply_message()
            if reply:
                if not text.strip():
                    text = reply.raw_text or reply.message or ""
                    saved_ents = dump_ents(reply.entities, shift=0)
                if reply.media:
                    media = await grab_welcome_media(client, event.chat_id, reply)
        if event.media and not media:
            media = await grab_welcome_media(client, event.chat_id, event.message)
        buttons = []
        if text:
            for label, url in BTN_RE.findall(text):
                buttons.append({"text": label, "url": url})
            cleaned = BTN_RE.sub("", text)
            if cleaned != text:
                text = cleaned.replace(" | ", "\n").strip()
                saved_ents = []
        if not text.strip():
            text = DEFAULT_WELCOME
            saved_ents = []
        uset(event.chat_id, welcome_text=text, welcome_media=str(media or ""), welcome_buttons=buttons, welcome_entities=saved_ents, welcome_custom=True, welcome=True)
        await say(client, event, "welcome save premium emoji rakhe welcome on")
        chat = await event.get_chat()
        await send_welcome(client, event.chat_id, sender, getattr(chat, "title", "") or "", force=True)

    @client.on(events.ChatAction)
    async def joined(event):
        if not (event.user_joined or event.user_added):
            return
        user = await event.get_user()
        if not user or user.bot:
            return
        chat = await event.get_chat()
        await send_welcome(client, event.chat_id, user, getattr(chat, "title", "") or "")

    @client.on(events.NewMessage(pattern=r"^/(biolink|nolinks|noswear|nophone|nohashtag|noforward|nobotpromo|longmode|nomedia|editprotect|anticheat)(@\w+)?"))
    async def toggles(event):
        if event.is_private:
            return
        sender = await event.get_sender()
        if not await is_admin(await event.get_chat(), sender.id):
            return
        cmd = (event.raw_text or "").split()[0].lstrip("/").split("@")[0].lower()
        key = TOGGLE_CMDS[cmd]
        parts = [p for p in (event.raw_text or "").split() if not p.startswith("@")]
        if len(parts) == 1:
            await event.reply(f"{cmd} {onoff(bool(gset(event.chat_id).get(key)))}")
            return
        if cmd == "longmode" and parts[1].isdigit():
            uset(event.chat_id, long_limit=int(parts[1]), longmode=True)
            await event.reply(f"longmode ON limit {parts[1]}")
            return
        flag = parts[1].lower() in {"on", "true", "1"}
        uset(event.chat_id, **{key: flag})
        await event.reply(f"{cmd} {onoff(flag)}")

    @client.on(events.NewMessage(pattern=r"^/(settings)(@\w+)?"))
    async def settings(event):
        if event.is_private:
            return
        s = gset(event.chat_id)
        parts = [p for p in (event.raw_text or "").split() if not p.startswith("@")]
        if len(parts) == 1:
            await event.reply(f"admin_only {s['admin_only']}\ncooldown {s['cooldown']}\nbatch {s['batch']} delay {s['delay']}\nwelcome {onoff(s['welcome'])}")
            return
        sender = await event.get_sender()
        if not await is_admin(await event.get_chat(), sender.id) or len(parts) < 3:
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
        approved = list(gset(event.chat_id).get("approved") or [])
        cmd = (event.raw_text or "").split()[0]
        if "unapprove" in cmd:
            approved = [x for x in approved if x != target.id]
        elif target.id not in approved:
            approved.append(target.id)
        uset(event.chat_id, approved=approved)
        await event.reply("Unapproved." if "unapprove" in cmd else "Approved.")

    @client.on(events.NewMessage(pattern=r"^/(warn|unwarn)(@\w+)?"))
    async def warn(event):
        if event.is_private or not event.is_reply:
            return
        sender = await event.get_sender()
        chat = await event.get_chat()
        if not await is_admin(chat, sender.id):
            return
        target = await (await event.get_reply_message()).get_sender()
        warns = dict(gset(event.chat_id).get("warns") or {})
        key = str(target.id)
        cmd = (event.raw_text or "").split()[0]
        if "unwarn" in cmd:
            warns[key] = max(0, int(warns.get(key, 0)) - 1)
        else:
            warns[key] = int(warns.get(key, 0)) + 1
        uset(event.chat_id, warns=warns)
        await event.reply(f"Warns: {warns[key]}")
        if warns[key] >= 3 and "unwarn" not in cmd:
            try:
                await client(EditBannedRequest(chat, target.id, ChatBannedRights(until_date=None, send_messages=True)))
                await event.reply("3 warns - muted.")
            except Exception as exc:
                await event.reply(f"Mute fail {type(exc).__name__}")

    @client.on(events.NewMessage(pattern=r"^/(truth|dare|tod|spin|love|flirt)(@\w+)?"))
    async def fun(event):
        cmd = (event.raw_text or "").split()[0].lstrip("/").split("@")[0].lower()
        if cmd == "love":
            await event.reply(f"Love meter: {random.randint(1, 100)}%")
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
            await event.reply(f"{pair['an']} + {pair['bn']}" if pair else "No couple.")
            return
        if cmd == "breakup":
            COUPLES.pop(str(event.chat_id), None)
            await event.reply("Breakup.")
            return
        if event.is_private or not event.is_reply:
            await event.reply("Reply karke /couple")
            return
        a = await event.get_sender()
        b = await (await event.get_reply_message()).get_sender()
        COUPLES[str(event.chat_id)] = {"an": a.first_name, "bn": b.first_name}
        await event.reply(f"{a.first_name} + {b.first_name}")

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
        if not sender or sender.bot or await is_admin(await event.get_chat(), sender.id):
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
        if not sender or sender.bot or await is_admin(await event.get_chat(), sender.id):
            return
        try:
            await event.delete()
        except Exception:
            pass

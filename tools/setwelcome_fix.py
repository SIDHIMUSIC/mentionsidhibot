"""Keep user premium emoji when /setwelcome is used."""

from telethon import events
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.tl.types import ChannelParticipantAdmin, ChannelParticipantCreator

from config import CONFIG
from tools.store import DEFAULT_WELCOME, uset
from tools.style import dump_ents, say, utf16_len
from tools.welcome import extract_buttons_keep_ents, grab_welcome_media, send_welcome, setwelcome_prefix

OWNER_ID = int(CONFIG["owner_id"])


async def _admin(client, chat, user_id: int) -> bool:
    if user_id == OWNER_ID:
        return True
    try:
        result = await client(GetParticipantRequest(chat, user_id))
    except Exception:
        return False
    return isinstance(result.participant, (ChannelParticipantAdmin, ChannelParticipantCreator))


def register_setwelcome(client) -> None:
    @client.on(events.NewMessage(pattern=r"^/(setwelcome)(@\w+)?"))
    async def setwelcome_keep(event):
        if event.is_private:
            return
        sender = await event.get_sender()
        if not await _admin(client, await event.get_chat(), sender.id):
            return
        raw = event.raw_text or event.message.message or ""
        prefix = setwelcome_prefix(raw)
        text = raw[len(prefix):] if prefix else ""
        saved_ents = dump_ents(event.message.entities, shift=utf16_len(prefix)) if text else []
        media = ""
        if event.is_reply:
            reply = await event.get_reply_message()
            if reply:
                if not (text or "").strip():
                    text = reply.raw_text or reply.message or ""
                    saved_ents = dump_ents(reply.entities, shift=0)
                if reply.media:
                    media = await grab_welcome_media(client, event.chat_id, reply)
        if event.media and not media:
            media = await grab_welcome_media(client, event.chat_id, event.message)
        buttons = []
        if text:
            text, buttons, saved_ents = extract_buttons_keep_ents(text, saved_ents)
        if not (text or "").strip():
            text = DEFAULT_WELCOME
            saved_ents = []
        uset(
            event.chat_id,
            welcome_text=text,
            welcome_media=str(media or ""),
            welcome_buttons=buttons,
            welcome_entities=saved_ents,
            welcome_custom=True,
            welcome=True,
        )
        await say(client, event, "welcome save. premium emoji rakhe")
        chat = await event.get_chat()
        await send_welcome(client, event.chat_id, sender, getattr(chat, "title", "") or "", force=True)

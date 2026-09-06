"""Reset saved custom welcome back to normal auto welcome."""

from telethon import events

from tools.store import DEFAULT_WELCOME, uset
from tools.style import say
from tools.welcome import send_welcome
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.tl.types import ChannelParticipantAdmin, ChannelParticipantCreator
from config import CONFIG

OWNER_ID = int(CONFIG["owner_id"])


async def _admin(client, chat, user_id: int) -> bool:
    if user_id == OWNER_ID:
        return True
    try:
        result = await client(GetParticipantRequest(chat, user_id))
    except Exception:
        return False
    return isinstance(result.participant, (ChannelParticipantAdmin, ChannelParticipantCreator))


def reset_welcome(chat_id: int) -> None:
    uset(
        chat_id,
        welcome_custom=False,
        welcome_text=DEFAULT_WELCOME,
        welcome_entities=[],
        welcome_media="",
        welcome_buttons=[],
        welcome=True,
    )


def register_clean(client) -> None:
    @client.on(events.NewMessage(pattern=r"^/(cleanwelcome|resetwelcome)(@\w+)?"))
    async def cleanwelcome_reset(event):
        if event.is_private:
            return
        sender = await event.get_sender()
        if not await _admin(client, await event.get_chat(), sender.id):
            return
        parts = [p for p in (event.raw_text or "").split() if not p.startswith("@")]
        arg = parts[1].lower() if len(parts) > 1 else "reset"
        if arg in {"on", "true", "1"}:
            uset(event.chat_id, cleanwelcome=True)
            await say(client, event, "old welcome auto delete on")
            return
        if arg in {"off", "false", "0"}:
            uset(event.chat_id, cleanwelcome=False)
            await say(client, event, "old welcome auto delete off")
            return
        reset_welcome(event.chat_id)
        await say(client, event, "saved welcome clean\nab group mein normal auto welcome chalega")

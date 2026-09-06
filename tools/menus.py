"""Start / help / guard / welcome button layouts."""

from config import CONFIG
from tools.store import gset
from tools.style import btn, sc

OWNER_URL = CONFIG["owner_url"]
SUPPORT_URL = CONFIG["support_url"]
MUSIC_BOT_URL = CONFIG["music_bot_url"]
UPDATES_URL = CONFIG.get("updates_url", SUPPORT_URL)


def start_caption() -> str:
    from tools.runtime import bot_name, ME_USERNAME as handle

    tag = f"@{handle}" if handle else bot_name()
    return (
        f"ɪᴛꜱ ᴍᴇ — {bot_name()}\n"
        f"{tag}\n\n"
        "ꜱᴍᴀʀᴛ ᴛᴀɢ ʙᴏᴛ ғᴏʀ ɢʀᴏᴜᴘꜱ\n"
        "ᴘʀᴇᴍɪᴜᴍ ᴛᴀɢ + ɢᴀᴍᴇꜱ + ɢᴜᴀʀᴅ\n"
        "ᴀᴅᴅ ɪɴ ɢʀᴏᴜᴘ · ᴍᴀᴋᴇ ᴀᴅᴍɪɴ · ᴜꜱᴇ /uᴛᴀɢ"
    )


def help_home() -> str:
    return (
        "ʜᴇʟᴘ ᴄᴇɴᴛᴇʀ — ꜱᴇʟᴇᴄᴛ ᴄᴀᴛᴇɢᴏʀʏ\n\n"
        "ᴛᴀɢ ꜱʏꜱᴛᴇᴍ — ᴍᴇᴍʙᴇʀꜱ & ᴀᴅᴍɪɴꜱ ᴛᴀɢ\n"
        "ᴄᴏᴜᴘʟᴇꜱ — 24ʜ / ᴘᴇʀᴍ ᴄᴏᴜᴘʟᴇ ꜱᴇᴛ\n"
        "ɢᴀᴍᴇꜱ — ᴛʀᴜᴛʜ ᴅᴀʀᴇ ꜱᴘɪɴ ʟᴏᴠᴇ\n"
        "ᴜꜱᴇʀ ᴛᴏᴏʟꜱ — ɪᴅ ᴘɪɴɢ ᴀғᴋ ꜱᴛᴀᴛꜱ\n"
        "ᴡᴇʟᴄᴏᴍᴇ — ɴᴇᴡ ᴍᴇᴍʙᴇʀ ᴍꜱɢ ᴏɴ/ᴏꜱꜱ\n"
        "ꜱᴇᴛᴛɪɴɢꜱ — ɢʀᴏᴜᴘ ᴛᴀɢ ᴏᴘᴛɪᴏɴꜱ\n"
        "ꜱᴇᴄᴜʀɪᴛʏ ɢᴜᴀʀᴅ — 14 ᴘʀᴏᴛᴇᴄᴛ ᴍᴏᴅᴜʟᴇꜱ"
    )


def start_buttons():
    from tools.runtime import ME_USERNAME as handle

    add_url = f"https://t.me/{handle}?startgroup=true" if handle else SUPPORT_URL
    return [
        [btn("ʜᴇʟᴘ", callback_data="menu:help", pe_name="help")],
        [btn("ᴀᴅᴅ ᴛᴏ ɢʀᴏᴜᴘ", url=add_url, pe_name="add")],
        [
            btn("ѕᴜᴘᴘᴏʀᴛ", url=SUPPORT_URL, pe_name="support"),
            btn("ᴏᴡɴᴇʀ", url=OWNER_URL, pe_name="owner"),
        ],
        [
            btn("ɢᴀᴍᴇ", callback_data="menu:games", pe_name="game"),
            btn("ᴜᴘᴅᴀᴛᴇꜱ", url=UPDATES_URL, pe_name="updates"),
        ],
        [btn("ᴍᴜꜱɪᴄ ʙᴏᴛ", url=MUSIC_BOT_URL, pe_name="music")],
    ]


def help_buttons():
    return [
        [
            btn("ᴛᴀɢ ꜱʏꜱᴛᴇᴍ", callback_data="menu:tag", pe_name="tag"),
            btn("ᴄᴏᴜᴘʟᴇꜱ", callback_data="menu:couples", pe_name="couples"),
        ],
        [
            btn("ɢᴀᴍᴇꜱ", callback_data="menu:games", pe_name="game"),
            btn("ᴜꜱᴇʀ ᴛᴏᴏʟꜱ", callback_data="menu:tools", pe_name="tools"),
        ],
        [
            btn("ᴡᴇʟᴄᴏᴍᴇ", callback_data="menu:welcome", pe_name="welcome"),
            btn("ꜱᴇᴛᴛɪɴɢꜱ", callback_data="menu:gset", pe_name="settings"),
        ],
        [btn("ꜱᴇᴄᴜʀɪᴛʏ ɢᴜᴀʀᴅ", callback_data="menu:security", pe_name="security")],
        [btn("ʙᴀᴄᴋ ᴛᴏ ꜱᴛᴀʀᴛ", callback_data="menu:start", pe_name="start")],
    ]


def guard_buttons():
    return [
        [btn("ᴀɴᴛɪ-ᴄʜᴇᴀᴛᴇʀ", callback_data="sec:anticheat", pe_name="anticheat"), btn("ᴀʙᴜꜱᴇ", callback_data="sec:abuse", pe_name="abuse")],
        [btn("ᴀᴘᴘʀᴏᴠᴀʟꜱ", callback_data="sec:approve", pe_name="approve"), btn("ʙɪᴏᴍᴏᴅᴇ", callback_data="sec:biolink", pe_name="biolink")],
        [btn("ᴍꜱɢᴅᴇʟᴇᴛᴇ", callback_data="sec:msgdel", pe_name="msgdel"), btn("ᴇᴅɪᴛ", callback_data="sec:edit", pe_name="edit")],
        [btn("ʟɪɴᴋꜱ", callback_data="sec:links", pe_name="links"), btn("ʟᴏɴɢᴍᴏᴅᴇ", callback_data="sec:long", pe_name="long")],
        [btn("ᴍᴇᴅɪᴀ", callback_data="sec:media", pe_name="media"), btn("ʙᴏᴛᴘʀᴏᴍᴏ", callback_data="sec:promo", pe_name="promo")],
        [btn("ғᴏʀᴡᴀʀᴅ", callback_data="sec:fwd", pe_name="fwd"), btn("ʜᴀꜱʜᴛᴀɢꜱ", callback_data="sec:hash", pe_name="hash")],
        [btn("ᴘʜᴏɴᴇ", callback_data="sec:phone", pe_name="phone"), btn("ᴍᴜᴛᴇ & ᴡᴀʀɴ", callback_data="sec:mute", pe_name="mute")],
        [btn("ʙᴀᴄᴋ ᴛᴏ ʜᴇʟᴘ", callback_data="menu:help", pe_name="back", style="success")],
    ]


def nav_row():
    return [[btn("ʙᴀᴄᴋ ᴛᴏ ʜᴇʟᴘ", callback_data="menu:help", pe_name="back"), btn("ꜱᴛᴀʀᴛ", callback_data="menu:start", pe_name="start")]]


def welcome_buttons():
    return [
        [btn("ᴡᴇʟᴄᴏᴍᴇ ᴏɴ", callback_data="do:welcome_on", pe_name="on", style="success"), btn("ᴡᴇʟᴄᴏᴍᴇ ᴏꜱꜱ", callback_data="do:welcome_off", pe_name="off", style="danger")],
        [btn("ᴄʟᴇᴀɴ ᴏɴ", callback_data="do:clean_on", pe_name="clean"), btn("ᴄʟᴇᴀɴ ᴏꜱꜱ", callback_data="do:clean_off", pe_name="clean")],
        *nav_row(),
    ]


def back_help():
    return [[btn("ꜱᴇᴄᴜʀɪᴛʏ", callback_data="menu:security", pe_name="security"), btn("ʙᴀᴄᴋ ᴛᴏ ʜᴇʟᴘ", callback_data="menu:help", pe_name="back")]]


def onoff(flag: bool) -> str:
    return sc("ᴏɴ") if flag else sc("ᴏꜱꜱ")


WELCOME_HELP = (
    "ᴡᴇʟᴄᴏᴍᴇ ꜱʏꜱᴛᴇᴍ\n\n"
    "» ᴄᴏᴍᴍᴀɴᴅꜱ\n"
    "• /setwelcome — ꜱᴇᴛ ᴡᴇʟᴄᴏᴍᴇ ᴍᴇꜱꜱᴀɢᴇ\n"
    "• /welcome on/off — ᴇɴᴀʙʟᴇ ᴏʀ ᴅɪꜱᴀʙʟᴇ ᴡᴇʟᴄᴏᴍᴇꜱ\n"
    "• /cleanwelcome on/off — ᴅᴇʟᴇᴛᴇ ᴏʟᴅ ᴡᴇʟᴄᴏᴍᴇꜱ\n\n"
    "» ꜱᴜᴘᴘᴏʀᴛᴇᴅ ᴘʟᴀᴄᴇʜᴏʟᴅᴇʀꜱ\n"
    "• {first_name} → ᴜꜱᴇʀ ғɪʀꜱᴛ ɴᴀᴍᴇ\n"
    "• {username} → @username\n"
    "• {id} → ᴜꜱᴇʀ ɪᴅ\n"
    "• {mention} → ᴄʟɪᴄᴋᴀʙʟᴇ ᴍᴇɴᴛɪᴏɴ\n"
    "• {title} → ɢʀᴏᴜᴘ ɴᴀᴍᴇ\n"
    "• {chatname} → ɢʀᴏᴜᴘ ɴᴀᴍᴇ\n\n"
    "» ʜᴏᴡ ᴛᴏ ꜱᴇᴛ\n"
    "• ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴍᴇꜱꜱᴀɢᴇ (ᴛᴇxᴛ/ᴘʜᴏᴛᴏ/ᴠɪᴅᴇᴏ) ᴡɪᴛʜ /setwelcome\n"
    "• ᴏʀ ꜱᴇɴᴅ ᴛᴇxᴛ ᴅɪʀᴇᴄᴛʟʏ\n\n"
    "» ʙᴜᴛᴛᴏɴꜱ ᴇxᴀᴍᴘʟᴇ\n"
    "[Rules](https://t.me/TG_BIO_STYLE) | [Support](https://t.me/TG_BIO_STYLE)\n\n"
    "» ᴛɪᴘ\n"
    "ʀᴇᴘʟʏ ᴛᴏ ᴍᴇᴅɪᴀ ᴛᴏ ꜱᴇᴛ ɪᴍᴀɢᴇ ᴡᴇʟᴄᴏᴍᴇ\n"
    "ꜱɪʀғ ᴏɴ = ɴᴀᴀᴍ ʟɪɴᴋ + ᴜꜱᴇʀɴᴀᴍᴇ + ɢʀᴏᴜᴘ\n"
    "ᴄᴜꜱᴛᴏᴍ ᴛᴇxᴛ = ᴘʟᴀᴄᴇʜᴏʟᴅᴇʀ + ᴘʀᴇᴍɪᴜᴍ ᴇᴍᴏջɪ"
)


def welcome_status_text(chat_id: int) -> str:
    s = gset(chat_id)
    return (
        WELCOME_HELP
        + "\n\n"
        + f"» ꜱᴛᴀᴛᴜꜱ  ᴡᴇʟᴄᴏᴍᴇ {onoff(s.get('welcome'))}"
        + f" · ᴄʟᴇᴀɴ {onoff(s.get('cleanwelcome'))}"
    )

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
        f"its me - {bot_name()}\n"
        f"{tag}\n\n"
        "smart tag bot for groups\n"
        "premium tag + games + guard\n"
        "add in group\n"
        "make admin\n"
        "use /utag"
    )


def help_home() -> str:
    return (
        "help center\n"
        "select category\n\n"
        "tag system\n"
        "couples\n"
        "games\n"
        "user tools\n"
        "welcome\n"
        "settings\n"
        "security guard"
    )


def start_buttons():
    from tools.runtime import ME_USERNAME as handle
    add_url = f"https://t.me/{handle}?startgroup=true" if handle else SUPPORT_URL
    return [
        [btn("help", callback_data="menu:help", pe_name="help")],
        [btn("add to group", url=add_url, pe_name="add")],
        [btn("support", url=SUPPORT_URL, pe_name="support")],
        [btn("owner", url=OWNER_URL, pe_name="owner")],
        [btn("game", callback_data="menu:games", pe_name="game")],
        [btn("updates", url=UPDATES_URL, pe_name="updates")],
        [btn("music bot", url=MUSIC_BOT_URL, pe_name="music")],
    ]


def help_buttons():
    return [
        [btn("tag system", callback_data="menu:tag", pe_name="tag")],
        [btn("couples", callback_data="menu:couples", pe_name="couples")],
        [btn("games", callback_data="menu:games", pe_name="game")],
        [btn("user tools", callback_data="menu:tools", pe_name="tools")],
        [btn("welcome", callback_data="menu:welcome", pe_name="welcome")],
        [btn("settings", callback_data="menu:gset", pe_name="settings")],
        [btn("security guard", callback_data="menu:security", pe_name="security")],
        [btn("back to start", callback_data="menu:start", pe_name="start")],
    ]


def guard_buttons():
    return [
        [btn("anti-cheater", callback_data="sec:anticheat", pe_name="anticheat")],
        [btn("abuse", callback_data="sec:abuse", pe_name="abuse")],
        [btn("approvals", callback_data="sec:approve", pe_name="approve")],
        [btn("biomode", callback_data="sec:biolink", pe_name="biolink")],
        [btn("msgdelete", callback_data="sec:msgdel", pe_name="msgdel")],
        [btn("edit", callback_data="sec:edit", pe_name="edit")],
        [btn("links", callback_data="sec:links", pe_name="links")],
        [btn("longmode", callback_data="sec:long", pe_name="long")],
        [btn("media", callback_data="sec:media", pe_name="media")],
        [btn("botpromo", callback_data="sec:promo", pe_name="promo")],
        [btn("forward", callback_data="sec:fwd", pe_name="fwd")],
        [btn("hashtags", callback_data="sec:hash", pe_name="hash")],
        [btn("phone", callback_data="sec:phone", pe_name="phone")],
        [btn("mute & warn", callback_data="sec:mute", pe_name="mute")],
        [btn("back to help", callback_data="menu:help", pe_name="back")],
    ]


def nav_row():
    return [
        [btn("back to help", callback_data="menu:help", pe_name="back")],
        [btn("start", callback_data="menu:start", pe_name="start")],
    ]


def welcome_buttons():
    return [
        [btn("welcome on", callback_data="do:welcome_on", pe_name="on")],
        [btn("welcome off", callback_data="do:welcome_off", pe_name="off")],
        [btn("clean on", callback_data="do:clean_on", pe_name="clean")],
        [btn("clean off", callback_data="do:clean_off", pe_name="clean")],
        [btn("support", url=SUPPORT_URL, pe_name="support")],
        [btn("updates", url=UPDATES_URL, pe_name="updates")],
        [btn("back to help", callback_data="menu:help", pe_name="back")],
        [btn("start", callback_data="menu:start", pe_name="start")],
    ]


def back_help():
    return [
        [btn("security", callback_data="menu:security", pe_name="security")],
        [btn("back to help", callback_data="menu:help", pe_name="back")],
    ]


def onoff(flag: bool) -> str:
    return sc("on") if flag else sc("off")


TAG_HELP = "tag system\n/utag\n/tagall\n/everyone\n@all\n/atag\n/admins\n@admins\n/bots\n/cancel\n/speed turbo\n/speed fast\n/speed normal\n/speed slow"
COUPLES_HELP = "couples\n/couple\n/pcouple\n/mycouple\n/breakup\n/flirt"
GAMES_HELP = "games\n/truth\n/dare\n/tod\n/spin\n/love"
TOOLS_HELP = "user tools\n/id\n/ping\n/afk"
GSET_HELP = "group settings\n/settings\n/speed 2\n/welcome on\n/welcome off"
SECURITY_HELP = "security guard\nanti-cheater\nabuse\napprovals\nbiomode\nedit\nlinks\nlongmode\nmedia\nbotpromo\nforward\nhashtags\nphone\nmute warn"

WELCOME_HELP = (
    "welcome system\n\n"
    "commands\n"
    "/setwelcome - set welcome message\n"
    "/welcome on\n"
    "/welcome off\n"
    "/cleanwelcome on\n"
    "/cleanwelcome off\n\n"
    "supported placeholders\n"
    "{first_name} - user first name\n"
    "{username} - @username\n"
    "{id} - user id\n"
    "{mention} - clickable mention\n"
    "{title} - group name\n"
    "{chatname} - group name\n\n"
    "how to set\n"
    "reply to a message text/photo/video with /setwelcome\n"
    "or send text directly\n\n"
    "buttons example\n"
    "[Rules](https://t.me/TG_BIO_STYLE)\n"
    "[Support](https://t.me/TG_BIO_STYLE)\n\n"
    "tip\n"
    "reply to media to set image welcome\n"
    "sirf on = name link + username + group\n"
    "custom text = placeholder + premium emoji\n"
    "no button given = updates + support auto"
)

SEC_PAGES = {
    "sec:anticheat": "anti-cheater\n/anticheat on\n/anticheat off",
    "sec:abuse": "abuse filter\n/noswear on\n/noswear off",
    "sec:approve": "approvals\n/approve reply\n/unapprove reply",
    "sec:biolink": "biomode\n/biolink on\n/biolink off",
    "sec:msgdel": "msgdelete\n/nolinks\n/noswear\n/nophone\n/nohashtag\n/noforward\n/nobotpromo\n/longmode\n/nomedia",
    "sec:edit": "edit protect\n/editprotect on\n/editprotect off",
    "sec:links": "links\n/nolinks on\n/nolinks off",
    "sec:long": "longmode\n/longmode on\n/longmode off\n/longmode 500",
    "sec:media": "media\n/nomedia on\n/nomedia off",
    "sec:promo": "botpromo\n/nobotpromo on\n/nobotpromo off",
    "sec:fwd": "forward\n/noforward on\n/noforward off",
    "sec:hash": "hashtags\n/nohashtag on\n/nohashtag off",
    "sec:phone": "phone\n/nophone on\n/nophone off",
    "sec:mute": "mute warn\n/warn reply\n/unwarn reply\n3 warn = mute",
}


def welcome_status_text(chat_id: int) -> str:
    s = gset(chat_id)
    return WELCOME_HELP + "\n\nstatus welcome " + onoff(s.get("welcome")) + "\nclean " + onoff(s.get("cleanwelcome"))


def menu_payload(data: str):
    pages = {
        "menu:start": (start_caption(), start_buttons()),
        "menu:help": (help_home(), help_buttons()),
        "menu:tag": (TAG_HELP, nav_row()),
        "menu:couples": (COUPLES_HELP, nav_row()),
        "menu:games": (GAMES_HELP, nav_row()),
        "menu:tools": (TOOLS_HELP, nav_row()),
        "menu:welcome": (WELCOME_HELP, welcome_buttons()),
        "menu:gset": (GSET_HELP, nav_row()),
        "menu:security": (SECURITY_HELP, guard_buttons()),
    }
    if data in pages:
        return pages[data]
    if data in SEC_PAGES:
        return SEC_PAGES[data], back_help()
    return None

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
        "add in group · make admin · use /utag"
    )


def help_home() -> str:
    return (
        "help center - select category\n\n"
        "tag system - members and admins tag\n"
        "couples - 24h / perm couple set\n"
        "games - truth dare spin love\n"
        "user tools - id ping afk stats\n"
        "welcome - new member msg on/off\n"
        "settings - group tag options\n"
        "security guard - 14 protect modules"
    )


def start_buttons():
    from tools.runtime import ME_USERNAME as handle
    add_url = f"https://t.me/{handle}?startgroup=true" if handle else SUPPORT_URL
    return [
        [btn("add to group", url=add_url, pe_name="add", style="success")],
        [btn("owner", url=OWNER_URL, pe_name="owner", style="primary"), btn("game", callback_data="menu:games", pe_name="game", style="primary")],
        [btn("help & commands", callback_data="menu:help", pe_name="help", style="primary")],
        [btn("support", url=SUPPORT_URL, pe_name="support", style="primary"), btn("music bot", url=MUSIC_BOT_URL, pe_name="music", style="danger")],
    ]


def help_buttons():
    return [
        [btn("tag system", callback_data="menu:tag", pe_name="tag", style="primary"), btn("couples", callback_data="menu:couples", pe_name="couples", style="danger")],
        [btn("games", callback_data="menu:games", pe_name="game", style="success"), btn("user tools", callback_data="menu:tools", pe_name="tools", style="primary")],
        [btn("welcome", callback_data="menu:welcome", pe_name="welcome", style="success"), btn("settings", callback_data="menu:gset", pe_name="settings", style="primary")],
        [btn("security guard", callback_data="menu:security", pe_name="security", style="danger")],
        [btn("back to start", callback_data="menu:start", pe_name="start", style="primary")],
    ]


def guard_buttons():
    return [
        [btn("anti-cheater", callback_data="sec:anticheat", pe_name="anticheat", style="danger"), btn("abuse", callback_data="sec:abuse", pe_name="abuse", style="danger")],
        [btn("approvals", callback_data="sec:approve", pe_name="approve", style="success"), btn("biomode", callback_data="sec:biolink", pe_name="biolink", style="primary")],
        [btn("msgdelete", callback_data="sec:msgdel", pe_name="msgdel", style="danger"), btn("edit", callback_data="sec:edit", pe_name="edit", style="primary")],
        [btn("links", callback_data="sec:links", pe_name="links", style="primary"), btn("longmode", callback_data="sec:long", pe_name="long", style="primary")],
        [btn("media", callback_data="sec:media", pe_name="media", style="success"), btn("botpromo", callback_data="sec:promo", pe_name="promo", style="danger")],
        [btn("forward", callback_data="sec:fwd", pe_name="fwd", style="primary"), btn("hashtags", callback_data="sec:hash", pe_name="hash", style="primary")],
        [btn("phone", callback_data="sec:phone", pe_name="phone", style="primary"), btn("mute & warn", callback_data="sec:mute", pe_name="mute", style="danger")],
        [btn("back to help", callback_data="menu:help", pe_name="back", style="primary")],
    ]


def nav_row():
    return [[btn("back to help", callback_data="menu:help", pe_name="back", style="primary"), btn("start", callback_data="menu:start", pe_name="start", style="success")]]


def welcome_buttons():
    return [
        [btn("welcome on", callback_data="do:welcome_on", pe_name="on", style="success"), btn("welcome off", callback_data="do:welcome_off", pe_name="off", style="danger")],
        [btn("clean on", callback_data="do:clean_on", pe_name="clean", style="success"), btn("clean off", callback_data="do:clean_off", pe_name="clean", style="danger")],
        [btn("support", url=SUPPORT_URL, pe_name="support", style="primary")],
        [btn("back to help", callback_data="menu:help", pe_name="back", style="primary"), btn("start", callback_data="menu:start", pe_name="start", style="success")],
    ]


def back_help():
    return [[btn("security", callback_data="menu:security", pe_name="security", style="danger"), btn("back to help", callback_data="menu:help", pe_name="back", style="primary")]]


def onoff(flag: bool) -> str:
    return sc("on") if flag else sc("off")


TAG_HELP = (
    "tag system\n\n"
    "/utag\n"
    "/tagall\n"
    "/everyone\n"
    "@all\n"
    "/atag\n"
    "/admins\n"
    "@admins\n"
    "/bots\n"
    "/cancel\n"
    "/speed turbo\n"
    "/speed fast\n"
    "/speed normal\n"
    "/speed slow"
)
COUPLES_HELP = "couples\n\n/couple\n/pcouple\n/mycouple\n/breakup\n/flirt"
GAMES_HELP = "games\n\n/truth\n/dare\n/tod\n/spin\n/love"
TOOLS_HELP = "user tools\n\n/id\n/ping\n/afk"
GSET_HELP = "group settings\n\n/settings\n/speed 2\n/welcome on\n/welcome off"
SECURITY_HELP = "security guard\n\nanti-cheater · abuse · approvals\nbiomode · edit · links\nlongmode · media · botpromo\nforward · hashtags · phone\nmute warn"

WELCOME_HELP = (
    "welcome system\n\n"
    "commands\n"
    "/setwelcome\n"
    "/welcome on\n"
    "/welcome off\n\n"
    "supported placeholders\n"
    "{first_name}\n"
    "{username}\n"
    "{id}\n"
    "{mention}\n"
    "{title}\n"
    "{chatname}\n\n"
    "how to set\n"
    "reply to text/photo/video with /setwelcome\n"
    "or send text directly\n\n"
    "buttons example\n"
    "[Rules](https://t.me/TG_BIO_STYLE)\n"
    "[Support](https://t.me/TG_BIO_STYLE)\n\n"
    "tip\n"
    "reply to media to set image welcome\n"
    "sirf on = name link + username + group\n"
    "custom text = placeholder + premium emoji"
)

SEC_PAGES = {
    "sec:anticheat": "anti-cheater\n\n/anticheat on\n/anticheat off",
    "sec:abuse": "abuse filter\n\n/noswear on\n/noswear off",
    "sec:approve": "approvals\n\n/approve\n/unapprove",
    "sec:biolink": "biomode\n\n/biolink on\n/biolink off",
    "sec:msgdel": "msgdelete\n\n/nolinks\n/noswear\n/nophone\n/nohashtag\n/noforward\n/nobotpromo\n/longmode\n/nomedia",
    "sec:edit": "edit protect\n\n/editprotect on\n/editprotect off",
    "sec:links": "links\n\n/nolinks on\n/nolinks off",
    "sec:long": "longmode\n\n/longmode on\n/longmode off\n/longmode 500",
    "sec:media": "media\n\n/nomedia on\n/nomedia off",
    "sec:promo": "botpromo\n\n/nobotpromo on\n/nobotpromo off",
    "sec:fwd": "forward\n\n/noforward on\n/noforward off",
    "sec:hash": "hashtags\n\n/nohashtag on\n/nohashtag off",
    "sec:phone": "phone\n\n/nophone on\n/nophone off",
    "sec:mute": "mute warn\n\n/warn\n/unwarn",
}


def welcome_status_text(chat_id: int) -> str:
    s = gset(chat_id)
    return WELCOME_HELP + "\n\nstatus welcome " + onoff(s.get("welcome"))


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

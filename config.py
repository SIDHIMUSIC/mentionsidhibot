"""Single branding + premium-emoji config. Secrets stay in env."""

ARROW_EMOJI = 6285315214673975495
BORROW_EMOJI = 6257814874085136842

# Replace these when you send new IDs.
START_LINE_EMOJI = 5224736245665511429
WELCOME_LINE_EMOJI = 6127555770197219915

LINE_EMOJI_IDS = [ARROW_EMOJI, BORROW_EMOJI]

PE_NAMES = {
    "help": 6215361789538866270,
    "add": 6026256492619895014,
    "support": 5215394081911351762,
    "owner": 5280858699286471614,
    "game": 5426978447383615815,
    "updates": 6255991106417202590,
    "music": 6258295815933008550,
    "tag": 6147896245684803245,
    "couples": 6291916484918648855,
    "tools": 6226540867855847176,
    "welcome": 6127555770197219915,
    "settings": 5461117441612462242,
    "security": 5424972470023104089,
    "start": 5224736245665511429,
    "start_line": START_LINE_EMOJI,
    "welcome_line": WELCOME_LINE_EMOJI,
    "back": 5215377245639549895,
    "on": 6025929233291809651,
    "off": 6026088864341299395,
    "clean": 6327922952402637651,
    "anticheat": 6291772878392138827,
    "abuse": 6294204598680820475,
    "approve": 6023909739669229757,
    "biolink": 6026236216079290036,
    "msgdel": 6023924329673135034,
    "edit": 5388967063396045964,
    "links": 5231159468040935233,
    "long": 5370900820336319679,
    "media": 6294287714887933094,
    "promo": 6294262456185265300,
    "fwd": 6255672312469657724,
    "hash": 6269463714450117067,
    "phone": 6314113631818618057,
    "mute": 5424972470023104089,
    "arrow": ARROW_EMOJI,
    "borrow": BORROW_EMOJI,
}

CONFIG = {
    "owner_id": 8170572505,
    "owner_url": "https://t.me/SANATANI_BACCHA",
    "support_url": "https://t.me/TG_BIO_STYLE",
    "music_bot_url": "https://t.me/PRAGYA_ROBOT",
    "updates_url": "https://t.me/HARRYASHU",
    "start_photos": [
        "https://graph.org/file/a7cfa3177e640a3183040-84365c2f7f7ce016a7.jpg",
        "https://graph.org/file/14ae21cbc4215f39ca696-5f2c2bb782f485c144.jpg",
        "https://graph.org/file/144df9ccbe81c69207fd9-ac11feef0e06acd26a.jpg",
        "https://graph.org/file/b5abb00ac3a4895cfd417-8f2eec1cbaab320474.jpg",
        "https://graph.org/file/ad7d11c8c0ee8faa493d0-a5873ddfa72e104b7f.jpg",
        "https://graph.org/file/aef5fa079d2999b8798ac-b3acd2440c5ab5f86f.jpg",
    ],
    "premium_emoji_ids": list(PE_NAMES.values()),
    "pe_names": PE_NAMES,
    "line_emoji_ids": LINE_EMOJI_IDS,
    "arrow_emoji": ARROW_EMOJI,
    "borrow_emoji": BORROW_EMOJI,
    "start_line_emoji": START_LINE_EMOJI,
    "welcome_line_emoji": WELCOME_LINE_EMOJI,
}

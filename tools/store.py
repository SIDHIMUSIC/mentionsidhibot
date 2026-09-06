"""Per-group settings store."""

from __future__ import annotations

import json
import os
from pathlib import Path

DEFAULT_WELCOME = (
    "ᴡᴇʟᴄᴏᴍᴇ {mention}\n"
    "ᴜꜱᴇʀ {username}\n"
    "ɢʀᴏᴜᴘ {chatname}\n"
    "ꜱᴛᴀʏ · ᴇɴʜᴏʏ ᴛʜᴇ ᴄʜᴀᴛ"
)

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_FILE = DATA_DIR / "settings.json"

DEFAULTS = {
    "admin_only": True,
    "cooldown": 12,
    "batch": 5,
    "names": True,
    "delay": 2,
    "welcome": False,
    "welcome_text": DEFAULT_WELCOME,
    "welcome_media": "",
    "welcome_buttons": [],
    "welcome_entities": [],
    "welcome_custom": False,
    "cleanwelcome": False,
    "welcome_last": 0,
    "biolink": False,
    "nolinks": False,
    "noswear": False,
    "nophone": False,
    "nohashtag": False,
    "noforward": False,
    "nobotpromo": False,
    "longmode": False,
    "long_limit": 500,
    "nomedia": False,
    "editprotect": False,
    "anticheat": False,
    "approved": [],
    "warns": {},
}


def load_all() -> dict:
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save_all(payload: dict) -> None:
    SETTINGS_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


ALL = load_all()


def gset(chat_id: int) -> dict:
    merged = dict(DEFAULTS)
    merged.update(ALL.get(str(chat_id), {}))
    return merged


def uset(chat_id: int, **changes) -> dict:
    cur = gset(chat_id)
    cur.update(changes)
    ALL[str(chat_id)] = cur
    save_all(ALL)
    return cur

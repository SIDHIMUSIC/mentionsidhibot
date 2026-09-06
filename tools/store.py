"""Per-group settings. Mongo if MONGO_URI set, else JSON."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

log = logging.getLogger("mentionbot")

DEFAULT_WELCOME = (
    "ᴡᴇʟᴄᴏᴍᴇ {mention}\n"
    "ᴜꜱᴇʀ {username}\n"
    "ɢʀᴏᴜᴘ {chatname}\n"
    "ꜱᴛᴀʏ · ᴇɴʜᴏʏ ᴛʜᴇ ᴄʜᴀᴛ"
)

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_FILE = DATA_DIR / "settings.json"
USERS_FILE = DATA_DIR / "users.json"
CHATS_FILE = DATA_DIR / "chats.json"

DEFAULTS = {
    "admin_only": True,
    "cooldown": 12,
    "batch": 5,
    "names": True,
    "delay": 2,
    "welcome": True,
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

MONGO_URI = os.getenv("MONGO_URI") or os.getenv("MONGODB_URI") or ""
_mongo = None
col_settings = None
col_users = None
col_chats = None

if MONGO_URI:
    try:
        from pymongo import MongoClient

        _mongo = MongoClient(MONGO_URI, serverSelectionTimeoutMS=8000)
        db = _mongo[os.getenv("MONGO_DB", "mentionbot")]
        col_settings = db["settings"]
        col_users = db["users"]
        col_chats = db["chats"]
        log.info("mongo connected %s", db.name)
    except Exception as exc:
        log.warning("mongo failed, json fallback: %s", exc)
        _mongo = None
        col_settings = None


def _read(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_all() -> dict:
    if col_settings is not None:
        out = {}
        for doc in col_settings.find({}):
            key = str(doc.get("_id", ""))
            if key:
                row = dict(doc)
                row.pop("_id", None)
                out[key] = row
        return out
    return _read(SETTINGS_FILE)


def save_all(payload: dict) -> None:
    if col_settings is not None:
        for key, row in payload.items():
            col_settings.update_one({"_id": str(key)}, {"$set": row}, upsert=True)
        return
    _write(SETTINGS_FILE, payload)


ALL = load_all()
USERS = {} if col_users is not None else _read(USERS_FILE)
CHATS = {} if col_chats is not None else _read(CHATS_FILE)


def gset(chat_id: int) -> dict:
    merged = dict(DEFAULTS)
    merged.update(ALL.get(str(chat_id), {}))
    return merged


def uset(chat_id: int, **changes) -> dict:
    cur = gset(chat_id)
    cur.update(changes)
    ALL[str(chat_id)] = cur
    if col_settings is not None:
        col_settings.update_one({"_id": str(chat_id)}, {"$set": cur}, upsert=True)
    else:
        save_all(ALL)
    return cur


def touch_user(user_id: int, name: str = "") -> None:
    if not user_id:
        return
    key = str(user_id)
    if col_users is not None:
        col_users.update_one({"_id": key}, {"$set": {"name": name or ""}}, upsert=True)
        return
    USERS[key] = {"name": name or USERS.get(key, {}).get("name", "")}
    _write(USERS_FILE, USERS)


def touch_chat(chat_id: int, title: str = "") -> None:
    if not chat_id:
        return
    key = str(chat_id)
    if col_chats is not None:
        col_chats.update_one({"_id": key}, {"$set": {"title": title or ""}}, upsert=True)
        return
    CHATS[key] = {"title": title or CHATS.get(key, {}).get("title", "")}
    _write(CHATS_FILE, CHATS)


def count_users() -> int:
    if col_users is not None:
        return col_users.count_documents({})
    return len(USERS)


def count_chats() -> int:
    if col_chats is not None:
        return col_chats.count_documents({})
    extra = {k for k, v in ALL.items() if int(k) < 0} if ALL else set()
    return max(len(CHATS), len(extra))


def all_user_ids() -> list[int]:
    if col_users is not None:
        return [int(d["_id"]) for d in col_users.find({}, {"_id": 1})]
    return [int(k) for k in USERS.keys()]


def all_chat_ids() -> list[int]:
    if col_chats is not None:
        return [int(d["_id"]) for d in col_chats.find({}, {"_id": 1})]
    ids = {int(k) for k in CHATS.keys()}
    ids.update(int(k) for k in ALL.keys() if str(k).lstrip("-").isdigit() and int(k) < 0)
    return list(ids)

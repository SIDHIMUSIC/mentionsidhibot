"""Shared runtime state filled by bot.py on start."""

client = None
ME_NAME = "Bot"
ME_USERNAME = ""


def bot_name() -> str:
    return ME_NAME or "Bot"

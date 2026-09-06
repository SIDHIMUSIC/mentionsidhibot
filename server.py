#!/usr/bin/env python3
"""Tiny web process so Heroku health checks work. Telegram bot runs only on worker."""

import os

from aiohttp import web


async def health(_request):
    return web.json_response({"ok": True, "role": "web"})


def main() -> None:
    port = int(os.getenv("PORT", "8080"))
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    web.run_app(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()

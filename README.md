# MentionMayaBot

Telegram group mention bot — `@all`, `/tagall`, `/admins` jaisi commands. Admin-only by default, Hindi + English replies, cancel/stop, cooldown, aur Heroku/Railway deploy files ready.

Live repo: https://github.com/SIDHIMUSIC/mentionmayabot

## Features

- `/all`, `/tagall`, `/everyone`, `/mention` — group ke members ko batch mein mention
- Group mein `@all` / `#all` / `@everyone` likhne se bhi chalega
- `/admins` — sirf admins ko tag
- `/bots` — group ke bots list
- `/cancel` ya `/stop` — running mention turant band
- `/settings` — admin_only, cooldown, batch size, names on/off
- `/stats`, `/ping`, `/help`, `/start`
- Deleted accounts aur bots skip
- Flood-safe batches (default 5 mentions / message + delay)
- Health endpoint Heroku `PORT` pe (`/health`)

## Commands

| Command | Kaam |
|---|---|
| `/start` | Welcome |
| `/help` | Commands list |
| `/all [text]` | Sab members mention |
| `/tagall [text]` | Same as `/all` |
| `/admins [text]` | Admins mention |
| `/bots` | Bots list |
| `/cancel` | Mention stop |
| `/settings` | Current group settings |
| `/settings admin_only on/off` | Sirf admin use kar sake |
| `/settings cooldown 60` | Seconds mein cooldown |
| `/settings batch 5` | Mentions per message (3-8) |
| `/settings names on/off` | Naam dikhao ya silent tag |
| `/stats` | Group stats |
| `/ping` | Latency |

Reply karke bhi `/all Good morning` use kar sakte ho — message ke saath mention jayega.

## Setup (local)

1. [@BotFather](https://t.me/BotFather) se bot banao, token lo.
2. Bot ko group mein add karo **aur admin banao** (Members dekhne ke liye zaroori).
3. https://my.telegram.org se `API_ID` + `API_HASH` lo.
4. Clone:

```bash
git clone https://github.com/SIDHIMUSIC/mentionmayabot.git
cd mentionmayabot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

5. `.env` fill karo, phir:

```bash
python bot.py
```

## Heroku deploy

Heroku pe ab free dyno nahi milta. Eco/Basic plan chahiye.

1. App banao, Python buildpack set karo.
2. Config vars:

- `API_ID`
- `API_HASH`
- `BOT_TOKEN`
- `OWNER_ID` (optional)

3. Dyno: **worker** on karo (`worker: python bot.py`).
   Web dyno bhi chalega — bot `PORT` pe `/health` serve karta hai.

Git se:

```bash
heroku create mentionmayabot-ashu
heroku buildpacks:set heroku/python
heroku config:set API_ID=... API_HASH=... BOT_TOKEN=...
git push heroku main
heroku ps:scale worker=1
```

Deploy button ke liye `app.json` already repo mein hai.

## Railway / Render / Docker

```bash
docker build -t mentionmayabot .
docker run --env-file .env -p 8080:8080 mentionmayabot
```

Wahi 3 env vars set karo.

## Important

- Bot ko group **admin** banana zaroori hai, warna member list nahi milti.
- Badi groups mein mention thoda time lega — `/cancel` se rok sakte ho.
- Spam / harassment ke liye mat use karo. Default setting admin-only hai.
- Heroku filesystem temporary hai, settings restart pe reset ho sakti hain.

## License

MIT. Apne group ke hisaab se fork/customize karo.

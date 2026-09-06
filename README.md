# Mention Bot

Display name **BotFather wale bot ka naam** se aata hai. Code mein Maya / Pragya / Sidhi kuch hardcode nahi hai.

Repo: https://github.com/SIDHIMUSIC/mentionmayabot

## Look

- `/start` pe rotating photo + 4 buttons: Owner, Support, Music Bot, Add Group
- Har mentioned user ke baad alag premium emoji
- Messages mein stylish emoji set

## Env

```bash
API_ID=
API_HASH=
BOT_TOKEN=
OWNER_ID=0
OWNER_URL=https://t.me/your_owner
SUPPORT_URL=https://t.me/your_support
MUSIC_BOT_URL=https://t.me/your_music_bot
START_PHOTOS=https://i.imgur.com/one.jpg,https://i.imgur.com/two.jpg
```

## Commands

`/all` `/tagall` `/everyone` `@all` `#all` `/admins` `/bots` `/cancel` `/settings` `/stats` `/ping` `/help`

Bot ko group **admin** banana zaroori hai.

## Deploy

```bash
heroku create
heroku config:set API_ID=... API_HASH=... BOT_TOKEN=... OWNER_URL=... SUPPORT_URL=... MUSIC_BOT_URL=... START_PHOTOS=...
git push heroku main
heroku ps:scale worker=1
```

MIT.

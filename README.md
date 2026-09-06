# Mention Bot

Display name BotFather wale bot ka naam se aata hai.

Repo: https://github.com/SIDHIMUSIC/mentionmayabot

Branding ek hi file mein hai: `config.py`

- owner id / owner button
- support channel
- music bot
- start photos
- premium emoji IDs

## Commands

`/all` `/tagall` `/everyone` `@all` `#all` `/admins` `/bots` `/cancel` `/settings` `/stats` `/ping` `/help`

## Deploy

```bash
heroku create
heroku config:set API_ID=... API_HASH=... BOT_TOKEN=...
git push heroku main
heroku ps:scale worker=1
```

MIT.

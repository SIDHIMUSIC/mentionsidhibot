<p align="center">
  <img src="https://graph.org/file/acdf3c70f8756ce4ccaf1-715ef9ca52f1e4b966.jpg" width="420">
</p>

<h1 align="center">✨ Mention Bot ✨</h1>

<p align="center">
  <img src="https://img.shields.io/badge/Telegram-Mention-2AABEE?style=for-the-badge&logo=telegram&logoColor=white">
  <img src="https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white">
  <img src="https://img.shields.io/badge/Heroku-Ready-430098?style=for-the-badge&logo=heroku&logoColor=white">
  <img src="https://img.shields.io/badge/Premium-Emoji-ff4d6d?style=for-the-badge">
</p>

<p align="center"><b>Deploy ke baad bot ka naam BotFather wale account se aata hai.</b></p>

---

## 🚀 Quick Deploy

<p align="center">
  <a href="https://dashboard.heroku.com/new?template=https://github.com/SIDHIMUSIC/mentionsidhibot">
    <img src="https://img.shields.io/badge/⚡_Heroku_Deploy-430098?style=for-the-badge&logo=heroku&logoColor=white" alt="Deploy to Heroku">
  </a>
  &nbsp;
  <a href="https://github.com/SIDHIMUSIC/mentionsidhibot">
    <img src="https://img.shields.io/badge/⭐_GitHub_Repo-0D1117?style=for-the-badge&logo=github&logoColor=white" alt="GitHub">
  </a>
</p>

<p align="center">
  <a href="https://dashboard.heroku.com/new?template=https://github.com/SIDHIMUSIC/mentionsidhibot">
    <img src="https://www.herokucdn.com/deploy/button.svg" alt="Deploy">
  </a>
</p>

Button dabao → Heroku pe **owner / support / music / photos already filled** aayenge.
Sirf ye 3 khud daalna hai:

- `API_ID` → [my.telegram.org](https://my.telegram.org)
- `API_HASH` → [my.telegram.org](https://my.telegram.org)
- `BOT_TOKEN` → [@BotFather](https://t.me/BotFather)

---

## 💎 Features

- `/all` `/tagall` `/everyone` `@all` `#all`
- Har user ke baad premium custom emoji
- `/start` pe rotating photos + 4 buttons
- `/admins` `/bots` `/cancel` `/settings`

Branding file: [`config.py`](https://github.com/SIDHIMUSIC/mentionsidhibot/blob/main/config.py)

---

## ⚡ Commands

| Command | Work |
|---|---|
| `/start` | Photo + buttons |
| `/all` | Mention all |
| `/admins` | Mention admins |
| `/bots` | List bots |
| `/cancel` | Stop mention |
| `/settings` | Group options |
| `/help` | Help |

Bot ko group **admin** banana zaroori hai.

---

## ☁️ After deploy

```bash
heroku ps:scale worker=1
```

Repo: https://github.com/SIDHIMUSIC/mentionsidhibot

#!/usr/bin/env python3
from __future__ import annotations
import asyncio, json, logging, os, random, time
from pathlib import Path
from dotenv import load_dotenv
from telethon import Button, TelegramClient, events
from telethon.errors import FloodWaitError, UserNotParticipantError
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.tl.types import ChannelParticipantAdmin, ChannelParticipantCreator, MessageEntityCustomEmoji, MessageEntityTextUrl, User
from config import CONFIG
load_dotenv()
log = logging.getLogger('mentionbot')
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
API_ID = int(os.getenv('API_ID', '0'))
API_HASH = os.getenv('API_HASH', '')
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
OWNER_ID = int(CONFIG['owner_id'])
OWNER_URL = CONFIG['owner_url']
SUPPORT_URL = CONFIG['support_url']
MUSIC_BOT_URL = CONFIG['music_bot_url']
UPDATES_URL = CONFIG.get('updates_url', SUPPORT_URL)
START_PHOTOS = list(CONFIG['start_photos'])
PREMIUM_EMOJI_IDS = list(CONFIG['premium_emoji_ids'])
FALLBACK_EMOJI = '✨'
DATA_DIR = Path(os.getenv('DATA_DIR', 'data')); DATA_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_FILE = DATA_DIR / 'settings.json'
DEFAULT_SETTINGS = {'admin_only': True, 'cooldown': 12, 'batch': 5, 'names': True, 'delay': 2}
ME_NAME = 'Bot'; ME_USERNAME = ''

def bot_name():
    return ME_NAME or 'Bot'

def load_all_settings():
    if SETTINGS_FILE.exists():
        try: return json.loads(SETTINGS_FILE.read_text(encoding='utf-8'))
        except json.JSONDecodeError: return {}
    return {}

def save_all_settings(payload):
    SETTINGS_FILE.write_text(json.dumps(payload, indent=2), encoding='utf-8')
ALL_SETTINGS = load_all_settings()

def chat_settings(chat_id):
    merged = dict(DEFAULT_SETTINGS); merged.update(ALL_SETTINGS.get(str(chat_id), {})); return merged

def update_chat_settings(chat_id, **changes):
    current = chat_settings(chat_id); current.update(changes); ALL_SETTINGS[str(chat_id)] = current; save_all_settings(ALL_SETTINGS); return current

if not API_ID or not API_HASH or not BOT_TOKEN:
    raise SystemExit('Set API_ID, API_HASH and BOT_TOKEN')
client = TelegramClient('mentionbot', API_ID, API_HASH)
active_jobs = set(); last_run = {}; last_start = {}; stats = {'mentions_sent': 0, 'jobs': 0}; AFK = {}; COUPLES = {}

def utf16_len(text):
    return len(text.encode('utf-16-le')) // 2

def pick_emoji_id(index):
    return PREMIUM_EMOJI_IDS[index % len(PREMIUM_EMOJI_IDS)]

def build_mention_message(header, users, show_name, start_index):
    text = header + '\n\n'; entities = []
    for idx, user in enumerate(users):
        name = (user.first_name or 'member').replace(']', '').replace('[', '')
        if not show_name: name = '♡'
        if idx: text += ' '
        name_offset = utf16_len(text); text += name
        entities.append(MessageEntityTextUrl(offset=name_offset, length=utf16_len(name), url=f'tg://user?id={user.id}'))
        text += ' '; emoji_offset = utf16_len(text); text += FALLBACK_EMOJI
        entities.append(MessageEntityCustomEmoji(offset=emoji_offset, length=utf16_len(FALLBACK_EMOJI), document_id=pick_emoji_id(start_index + idx)))
    return text, entities

def start_caption():
    handle = f'@{ME_USERNAME}' if ME_USERNAME else bot_name()
    return f"\u2661 It's Me  —  {bot_name()}\n{handle}\n\n📌 A Smart Tag-Bot\nWorks in Groups & Private\nPremium Tag System\nGames · Fun Tools"

def help_home_text():
    return 'HELP CENTER\n\nTAG SYSTEM · COUPLES · GAMES · USER TOOLS · WELCOME · SECURITY'

def start_buttons():
    add_url = f'https://t.me/{ME_USERNAME}?startgroup=true' if ME_USERNAME else SUPPORT_URL
    return [[Button.url('♡ ADD ME TO YOUR GROUP', add_url)],[Button.url('owner', OWNER_URL), Button.inline('GAME', b'menu:games')],[Button.inline('HELP & COMMANDS', b'menu:help')],[Button.url('SUPPORT', SUPPORT_URL), Button.url('UPDATES', UPDATES_URL)]]

def help_buttons():
    return [[Button.inline('TAG SYSTEM', b'menu:tag'), Button.inline('COUPLES', b'menu:couples')],[Button.inline('GAMES', b'menu:games'), Button.inline('USER TOOLS', b'menu:tools')],[Button.inline('WELCOME', b'menu:welcome')],[Button.inline('SECURITY GUARD', b'menu:security')],[Button.inline('BACK TO START', b'menu:start')]]

def back_row():
    return [[Button.inline('BACK TO HELP', b'menu:help'), Button.inline('START', b'menu:start')]]

async def is_admin(chat, user_id):
    if OWNER_ID and user_id == OWNER_ID: return True
    try:
        result = await client(GetParticipantRequest(chat, user_id))
    except Exception:
        return False
    return isinstance(result.participant, (ChannelParticipantAdmin, ChannelParticipantCreator))

async def collect_members(chat, kind):
    members = []
    async for user in client.iter_participants(chat):
        if not isinstance(user, User) or user.deleted or user.is_self: continue
        if kind == 'all' and user.bot: continue
        if kind == 'admins':
            if user.bot: continue
            if not await is_admin(chat, user.id): continue
        if kind == 'bots' and not user.bot: continue
        members.append(user)
    return members

async def run_mention(event, kind, extra_text, force_admin=None):
    chat = await event.get_chat(); chat_id = event.chat_id; sender = await event.get_sender()
    if event.is_private:
        await event.reply('Sirf group mein chalti hai.'); return
    settings = chat_settings(chat_id)
    need_admin = settings['admin_only'] if force_admin is None else force_admin
    if need_admin and not await is_admin(chat, sender.id):
        await event.reply('Sirf admins mention chala sakte hain.'); return
    wait = settings['cooldown'] - (time.time() - last_run.get(chat_id, 0))
    if wait > 0 and chat_id not in active_jobs:
        await event.reply(f'Cooldown `{int(wait)}s` bacha hai.'); return
    if chat_id in active_jobs:
        await event.reply('Pehle se mention chal raha hai. /cancel'); return
    active_jobs.add(chat_id); stats['jobs'] += 1; last_run[chat_id] = time.time()
    batch = max(3, min(8, int(settings['batch']))); show_name = bool(settings['names'])
    try:
        members = await collect_members(chat, kind)
    except Exception as exc:
        active_jobs.discard(chat_id); await event.reply(f'Members nahi mile. Bot ko admin banao.\n`{type(exc).__name__}`'); return
    if not members:
        active_jobs.discard(chat_id); await event.reply('Koi member nahi mila.'); return
    header = extra_text.strip() if extra_text.strip() else f'{bot_name()} — sab yahan aao'
    status = await event.reply(f'Mention start — **{len(members)}**\n/cancel se rok sakte ho')
    sent = 0
    try:
        for i in range(0, len(members), batch):
            if chat_id not in active_jobs:
                await event.reply('Mention cancel ho gaya.'); return
            chunk = members[i:i+batch]
            body, entities = build_mention_message(header, chunk, show_name, i)
            try:
                await client.send_message(chat_id, body, formatting_entities=entities, link_preview=False)
            except FloodWaitError as flood:
                await asyncio.sleep(flood.seconds + 1)
                await client.send_message(chat_id, body, formatting_entities=entities, link_preview=False)
            sent += len(chunk); stats['mentions_sent'] += len(chunk)
            await asyncio.sleep(float(settings.get('delay', 2)))
    finally:
        active_jobs.discard(chat_id)
    done = f'Done  {sent}/{len(members)} mention ho gaye.'
    try: await status.edit(done)
    except Exception: await event.reply(done)

async def send_start(event, edit=False):
    chat_id = event.chat_id; now = time.time()
    if now - last_start.get(chat_id, 0) < 2: return
    last_start[chat_id] = now
    caption = start_caption(); buttons = start_buttons(); photo = random.choice(START_PHOTOS) if START_PHOTOS else None
    if photo:
        try:
            await client.send_file(chat_id, photo, caption=caption, buttons=buttons, reply_to=getattr(event, 'id', None)); return
        except Exception as exc:
            log.warning('start photo failed: %s', exc)
    await event.reply(caption, buttons=buttons)

@client.on(events.NewMessage(pattern=r'^/(start)(@\w+)?'))
async def start_handler(event):
    await send_start(event)

@client.on(events.NewMessage(pattern=r'^/(help)(@\w+)?'))
async def help_handler(event):
    await event.reply(help_home_text(), buttons=help_buttons())

@client.on(events.NewMessage(pattern=r'^/(ping)(@\w+)?'))
async def ping_handler(event):
    t0 = time.perf_counter(); msg = await event.reply('pong...'); await msg.edit(f'pong `{(time.perf_counter()-t0)*1000:.0f}ms`')

@client.on(events.NewMessage(pattern=r'^/(cancel|stop)(@\w+)?'))
async def cancel_handler(event):
    if event.is_private: return
    chat = await event.get_chat(); sender = await event.get_sender()
    if chat_settings(event.chat_id)['admin_only'] and not await is_admin(chat, sender.id):
        await event.reply('Cancel ke liye admin hona chahiye.'); return
    active_jobs.discard(event.chat_id); await event.reply('Mention stop.')

@client.on(events.NewMessage(pattern=r'^/(all|tagall|everyone|mention|utag)(@\w+)?'))
async def mention_cmd(event):
    extra = ''; raw = event.raw_text or ''; bits = raw.split(maxsplit=1)
    if len(bits) > 1 and not bits[1].startswith('@'): extra = bits[1]
    elif event.is_reply:
        reply = await event.get_reply_message()
        if reply and reply.raw_text: extra = reply.raw_text
    await run_mention(event, 'all', extra)

@client.on(events.NewMessage(pattern=r'^/(admins|admin|atag)(@\w+)?'))
async def admins_cmd(event):
    extra = ''; raw = event.raw_text or ''; bits = raw.split(maxsplit=1)
    if len(bits) > 1 and not bits[1].startswith('@'): extra = bits[1]
    await run_mention(event, 'admins', extra or 'Admins needed', force_admin=False)

@client.on(events.NewMessage(pattern=r'^/(bots)(@\w+)?'))
async def bots_cmd(event):
    if event.is_private:
        await event.reply('Group mein use karo.'); return
    chat = await event.get_chat(); title = getattr(chat, 'title', None) or 'group'
    bots = await collect_members(chat, 'bots')
    if not bots:
        await event.reply('Koi extra bot nahi mila.'); return
    lines = [f'**BOT LIST — {title}**\n', '🤖 BOTS']
    for i, bot in enumerate(bots):
        uname = f'@{bot.username}' if bot.username else (bot.first_name or str(bot.id))
        lines.append(('\u2514' if i == len(bots)-1 else '\u251c') + ' ' + uname)
    lines.append(f'\n**TOTAL NUMBER OF BOTS: {len(bots)}**')
    await event.reply('\n'.join(lines))

@client.on(events.CallbackQuery)
async def menu_clicks(event):
    data = event.data.decode() if event.data else ''
    pages = {
        'menu:help': (help_home_text(), help_buttons()),
        'menu:tag': ('TAG SYSTEM\n\n/utag /tagall /everyone admin only\n/atag /admin anyone\n/cancel /speed', back_row()),
        'menu:couples': ('COUPLES\n\n/couple reply\n/breakup /mycouple /flirt', back_row()),
        'menu:games': ('GAMES\n\n/truth /dare /tod /spin /love /kiss_marry_kill', back_row()),
        'menu:tools': ('TOOLS\n\n/id /ping /afk /user_stats', back_row()),
        'menu:welcome': ('WELCOME\n\nBot ko admin banao. /utag se members tag. Bots mention nahi hote.', back_row()),
        'menu:security': ('SECURITY\n\n/settings se tag control.', back_row()),
    }
    if data == 'menu:start':
        await event.answer(); await send_start(event); return
    if data in pages:
        text, buttons = pages[data]; await event.answer()
        try: await event.edit(text, buttons=buttons)
        except Exception: await event.reply(text, buttons=buttons)

@client.on(events.NewMessage(pattern=r'^/(speed)(@\w+)?'))
async def speed_cmd(event):
    if event.is_private: return
    chat = await event.get_chat(); sender = await event.get_sender()
    if not await is_admin(chat, sender.id):
        await event.reply('Speed sirf admin.'); return
    parts = [p for p in (event.raw_text or '').split() if not p.startswith('@')]
    presets = {'turbo':1,'fast':2,'normal':3,'slow':5,'reset':2}
    if len(parts)==1:
        await event.reply(f"Current `{chat_settings(event.chat_id).get('delay',2)}s`"); return
    val = parts[1].lower(); delay = presets.get(val)
    if delay is None:
        try: delay = max(1, min(10, int(val)))
        except ValueError:
            await event.reply('/speed 2'); return
    update_chat_settings(event.chat_id, delay=delay); await event.reply(f'Speed `{delay}s`')

@client.on(events.NewMessage(pattern=r'^/(id)(@\w+)?'))
async def id_cmd(event):
    if event.is_reply:
        user = await (await event.get_reply_message()).get_sender(); await event.reply(f'ID: `{user.id}`'); return
    sender = await event.get_sender(); await event.reply(f'Your ID: `{sender.id}`')

@client.on(events.NewMessage(pattern=r'^/(afk)(@\w+)?'))
async def afk_cmd(event):
    sender = await event.get_sender(); parts = (event.raw_text or '').split(maxsplit=1)
    AFK[sender.id] = parts[1] if len(parts)>1 else 'AFK'; await event.reply('AFK on')

@client.on(events.NewMessage(pattern=r'^/(truth|dare|tod|spin|love|flirt)(@\w+)?'))
async def fun_cmd(event):
    cmd = (event.raw_text or '').split()[0].lstrip('/').split('@')[0].lower()
    if cmd=='love': await event.reply(f'Love meter: **{random.randint(1,100)}%**'); return
    if cmd=='flirt': await event.reply(random.choice(['Wifi nahi, connection tumse hai.','Notification tumhara wait karta hoon.'])); return
    await event.reply(random.choice(['Truth: last lie kab?','Dare: stylish GM likho.','Spin: Lucky!']))

@client.on(events.NewMessage(incoming=True))
async def text_triggers(event):
    if not event.raw_text or event.is_private: return
    text = event.raw_text.strip().lower()
    if text.startswith('/'): return
    first = text.split(maxsplit=1)[0]
    if first not in {'@all','#all','@everyone','#everyone'} and text not in {'@all','#all','@everyone','#everyone'}: return
    extra = event.raw_text.split(maxsplit=1)[1] if len(event.raw_text.split(maxsplit=1))>1 else ''
    await run_mention(event, 'all', extra)

async def main():
    global ME_NAME, ME_USERNAME
    await client.start(bot_token=BOT_TOKEN)
    me = await client.get_me(); ME_NAME = (me.first_name or me.username or 'Bot').strip(); ME_USERNAME = me.username or ''
    log.info('Started as %s (@%s) worker only', ME_NAME, ME_USERNAME)
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())

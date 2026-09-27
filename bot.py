"""Personal KI-101 timetable bot. Python 3.10+."""
import getpass
import json
import re
import time
import urllib.request
import urllib.error
from pathlib import Path
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
DAYS = ['Понеділок', 'Вівторок', 'Середа', 'Четвер', 'П’ятниця', 'Субота', 'Неділя']
TIMES = ['08:30–09:50', '10:05–11:25', '11:40–13:00', '13:15–14:35', '14:50–16:10', '16:25–17:45', '18:00–19:20', '19:30–20:50']
KEYBOARD = {'keyboard': [['📅 Сьогодні', '➡️ Завтра'], ['🗓 На тиждень', '⏭ Наступний тиждень'], ['ℹ️ Про розклад']], 'resize_keyboard': True}

def load_schedule():
    return json.loads((ROOT / 'schedule.json').read_text(encoding='utf-8'))

def week_type(day, data):
    anchor = date.fromisoformat(data['numerator_monday'])
    monday = day - timedelta(days=day.weekday())
    return 'chys' if ((monday - anchor).days // 7) % 2 == 0 else 'znam'

def lessons_for(day, data):
    week = week_type(day, data)
    selected = []
    for lesson in data['lessons']:
        subgroup = 1 if lesson['subject'].startswith('Програмування') else 2
        if lesson['day'] == day.weekday() and lesson['week'] in ('full', week) and lesson['subgroup'] in (0, subgroup):
            selected.append(lesson)
    return sorted(selected, key=lambda x: x['number'])

def render_day(day, data):
    name = 'Чисельник' if week_type(day, data) == 'chys' else 'Знаменник'
    lines = [f'📅 {DAYS[day.weekday()]}, {day:%d.%m.%Y}', f'🎓 КІ-101 · {name}', '']
    lessons = lessons_for(day, data)
    if not lessons:
        lines.append('🎉 За збереженим розкладом занять немає!')
    for lesson in lessons:
        number = lesson['number']
        slot = lesson.get('time') or TIMES[number - 1]
        lines.extend([f'{number} пара · {slot}', lesson['subject'], lesson['details'], ''])
    if day < date.fromisoformat(data['valid_from']) or day > date.fromisoformat(data['review_after']):
        lines.append('⚠️ Перевір розклад нового періоду: ця копія може вже не діяти.')
    lines.append(f'Копія розкладу: {data["updated"]}. Заміни перевіряй на сайті.')
    return '\n'.join(lines)

def responses(text, today, data):
    if text in ('📅 Сьогодні', '/today'):
        return [render_day(today, data)]
    if text in ('➡️ Завтра', '/tomorrow'):
        return [render_day(today + timedelta(days=1), data)]
    if text in ('🗓 На тиждень', '/week', '⏭ Наступний тиждень'):
        monday = today - timedelta(days=today.weekday())
        if text == '⏭ Наступний тиждень':
            monday += timedelta(days=7)
        return [render_day(monday + timedelta(days=i), data) for i in range(7)]
    if text == 'ℹ️ Про розклад':
        return ['КІ-101\nПрограмування: 1-ша підгрупа.\nІноземна та інші предмети: 2-га підгрупа.\n'
                '28.09–04.10.2026 — чисельник; далі тижні чергуються.\nЧасовий пояс: Europe/Kyiv.\n'
                'Це збережена копія, а не автоматичне стеження за замінами.\n'
                'Оновлення: запусти update_schedule.bat на комп’ютері.\n'
                'Фізкультура: у джерелі окремо вказано 08:00–09:20.\n' + data['source']]
    return ['Привіт! 👋 Я показую твій розклад КІ-101.\nОбери «📅 Сьогодні», «➡️ Завтра» або тиждень кнопками нижче.']


import os
import hashlib
from flask import Flask, request, jsonify

app = Flask(__name__)
ZONE = ZoneInfo('Europe/Kyiv')

def api(token, method, payload):
    req = urllib.request.Request(
        'https://api.telegram.org/bot' + token + '/' + method,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req, timeout=40) as response:
        body = json.load(response)
    if not body.get('ok'):
        raise RuntimeError('Telegram API error')
    return body['result']

def get_token():
    token = os.environ.get('BOT_TOKEN', '').strip()
    if token:
        return token

    path = ROOT / '.env'
    if path.exists():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            if line.startswith('BOT_TOKEN='):
                token = line.split('=', 1)[1].strip()
                if token:
                    return token

    raise RuntimeError('BOT_TOKEN не заданий')

TOKEN = get_token()
WEBHOOK_SECRET = hashlib.sha256(TOKEN.encode('utf-8')).hexdigest()[:32]

def send_answers(message):
    if not message.get('text'):
        return
    if message.get('chat', {}).get('type') != 'private':
        return

    data = load_schedule()
    text = message['text'].split('@')[0]
    today = datetime.now(ZONE).date()

    for answer in responses(text, today, data):
        api(TOKEN, 'sendMessage', {
            'chat_id': message['chat']['id'],
            'text': answer,
            'reply_markup': KEYBOARD,
            'link_preview_options': {'is_disabled': True}
        })

@app.get('/')
def health():
    return 'KI-101 Telegram bot is running', 200

@app.post('/webhook')
def telegram_webhook():
    if request.headers.get('X-Telegram-Bot-Api-Secret-Token') != WEBHOOK_SECRET:
        return 'forbidden', 403

    update = request.get_json(silent=True) or {}
    message = update.get('message', {})

    try:
        send_answers(message)
    except Exception as error:
        print(f'Webhook error: {type(error).__name__}: {error}', flush=True)

    return jsonify(ok=True)

def configure_webhook():
    public_url = os.environ.get('RENDER_EXTERNAL_URL', '').rstrip('/')
    if not public_url:
        return

    webhook_url = public_url + '/webhook'
    result = api(TOKEN, 'setWebhook', {
        'url': webhook_url,
        'secret_token': WEBHOOK_SECRET,
        'allowed_updates': ['message'],
        'drop_pending_updates': False
    })
    print(f'Webhook configured: {webhook_url} ({result})', flush=True)

configure_webhook()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', '10000'))
    app.run(host='0.0.0.0', port=port)

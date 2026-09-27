ГОТОВО ДЛЯ БЕЗКОШТОВНОГО RENDER

Файли:
- bot.py
- schedule.json
- requirements.txt
- render.yaml
- .gitignore

1. Створи новий токен у @BotFather, якщо старий токен десь публікувався.
2. Завантаж ці файли в GitHub-репозиторій. Файл .env НЕ завантажуй.
3. На render.com: New -> Web Service -> підключи GitHub.
4. Plan: Free.
5. Build Command: pip install -r requirements.txt
6. Start Command: gunicorn bot:app
7. Environment -> додай BOT_TOKEN = твій новий токен.
8. Deploy.
9. Після статусу Live відкрий бота в Telegram і натисни /start.

Render автоматично задає RENDER_EXTERNAL_URL. Під час запуску bot.py сам реєструє
Telegram webhook на https://<твій-сервіс>.onrender.com/webhook.

ВАЖЛИВО:
На Free Render сервіс засинає після періоду без HTTP-трафіку. Наступне повідомлення
до Telegram-бота має розбудити його через webhook, тому перша відповідь після довгої
паузи може прийти із затримкою.

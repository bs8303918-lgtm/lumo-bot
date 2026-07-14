# Lumo — один запуск

Теперь **бот + API + Mini App** в одном процессе:

```powershell
cd C:\Users\User\Desktop\lumo-bot
.\.venv\Scripts\python main.py
```

Поднимается:
- Telegram-бот (polling)
- Мониторинг каналов + LLM
- HTTP на порту **8000**: `/api/*` и `/app/` (Mini App)

---

## Кнопка **Open** в Telegram

**Прод:** Mini App на Vercel — в `.env` / Railway:

```env
PUBLIC_BASE_URL=https://lumo-bot-production-9903.up.railway.app
TELEGRAM_WEBAPP_URL=https://lumo-bot.vercel.app
```

Кнопка **Price** открывает `https://lumo-bot.vercel.app/#pricing`.

Telegram требует **HTTPS**. Для локальной отладки без Vercel — туннель:

```powershell
cloudflared tunnel --url http://127.0.0.1:8000
```

```env
PUBLIC_BASE_URL=https://xxxx.trycloudflare.com
# лучше явно: TELEGRAM_WEBAPP_URL=https://xxxx.trycloudflare.com/app/
MINI_APP_MENU_TEXT=Open
```

Перезапусти бота — слева от поля ввода появится синяя кнопка **Open**.

---

## Переменные `.env`

| Переменная | Значение |
|------------|----------|
| `API_ENABLED` | `true` — API вместе с ботом |
| `AUTO_BUILD_WEBAPP` | `true` — собрать Mini App при старте, если нет `dist/` |
| `PUBLIC_BASE_URL` | HTTPS URL туннеля (без `/app`) |
| `MINI_APP_MENU_TEXT` | Текст кнопки, по умолчанию `Open` |
| `API_ALLOW_DEV_AUTH` | `true` — тест в браузере без Telegram |

---

## Проверка без Telegram

После запуска `main.py` открой: **http://localhost:8000/app/**

Во вкладке **Профиль** укажи Telegram ID (нужен `API_ALLOW_DEV_AUTH=true`).

---

## Структура

```
main.py              ← один процесс: бот + API + статика
api/app.py           ← /api/* + mount /app/
telegram-site/       ← исходники Mini App
scripts/build_webapp.py
```

Старые отдельные терминалы (`api_server.py`, `сайт/backend`, `npm run dev`) **больше не нужны** для работы бота.

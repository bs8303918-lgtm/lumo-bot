# Деплой Lumo на Railway (Hobby)

Railway крутит **worker** 24/7: мониторинг каналов, LLM, API, Mini App, отправка карточек.  
**Telegram polling** (`/start`, кнопки) — опционально на твоём ПК через `bot_main.py`.

---

## Архитектура

```
Railway (LUMO_MODE=worker)
  ├── Telethon → каналы
  ├── LLM (Groq/Gemini)
  ├── FastAPI :PORT → /api/, /app/
  ├── PostgreSQL (Railway или Supabase)
  └── send_message → пользователям (без polling)

Твой ПК (опционально, LUMO_MODE=bot)
  └── polling → /start, меню, FSM
```

> **Один токен бота = один polling.** На Railway polling **не** запускается (`worker` mode).

---

## 1. GitHub

Репозиторий: `https://github.com/bs8303918-lgtm/lumo-bot`

Railway: **New Project → Deploy from GitHub → lumo-bot**

---

## 2. PostgreSQL

### Вариант A — Supabase (рекомендуется, free tier)

1. [supabase.com](https://supabase.com) → New project  
2. **Settings → Database → Connection string → URI** (pooler, port **6543**)  
3. Railway → Variables:

```env
DATABASE_URL=postgresql://postgres.[ref]:[PASSWORD]@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
```

### Вариант B — Railway Postgres

1. Project → **Add Service → Database → PostgreSQL**  
2. В сервисе Lumo → Variables → **Add Reference** → `DATABASE_URL` из Postgres  
   (или `DATABASE_PRIVATE_URL` для internal)

---

## 3. Переменные окружения (Railway → lumo-bot → Variables)

**Обязательные:**

```env
LUMO_MODE=worker
DATABASE_URL=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_API_ID=...
TELEGRAM_API_HASH=...
TELEGRAM_ADMIN_CHAT_ID=...
LLM_PROVIDER=openai
OPENAI_API_KEY=...
OPENAI_BASE_URL=https://api.groq.com/openai/v1
OPENAI_MODEL=llama-3.1-8b-instant
PUBLIC_BASE_URL=https://YOUR-SERVICE.up.railway.app
AUTO_BUILD_WEBAPP=false
SKIP_INSTANCE_LOCK=true
```

**Telethon session (volume, см. шаг 4):**

```env
TELETHON_SESSION_PATH=/data/lumo_session
```

**После первого деплоя** скопируй домен Railway в `PUBLIC_BASE_URL` (Settings → Networking → Generate Domain).

---

## 4. Volume для Telethon (обязательно)

Без volume сессия Telethon **сотрётся** при каждом redeploy.

1. Railway → сервис **lumo-bot** → **Volumes**  
2. Mount path: `/data`  
3. Variable: `TELETHON_SESSION_PATH=/data/lumo_session`

### Первый логин Telethon

Railway → сервис → **Shell**:

```bash
python scripts/telethon_login_qr.py
```

Отсканируй QR в Telegram → **Настройки → Устройства**.  
Проверка: `/health` в боте → Telethon ✅

---

## 5. Деплой

Push в `main` → Railway собирает Dockerfile автоматически.

Логи: Railway → **Deployments → View logs**

Ожидай:

```
Starting Lumo (mode=worker)...
API + Mini App on http://0.0.0.0:8000
Monitor cycle: N channels to check
```

Health: `https://YOUR-SERVICE.up.railway.app/api/health`

Mini App: `https://YOUR-SERVICE.up.railway.app/app/`

---

## 6. Бот на ПК (polling)

`.env` на компьютере:

```env
LUMO_MODE=bot
DATABASE_URL=...тот же что на Railway...
TELEGRAM_BOT_TOKEN=...тот же...
# Telethon и LLM на ПК не нужны
```

Запуск:

```powershell
cd C:\Users\User\Desktop\lumo-bot
.\.venv\Scripts\Activate.ps1
python bot_main.py
```

Пока ПК выключен — команды `/start` не работают, но **карточки и API на Railway работают**.

---

## 7. Vercel (Mini App отдельно, опционально)

Если фронт на Vercel:

```env
VITE_API_URL=https://YOUR-SERVICE.up.railway.app
TELEGRAM_WEBAPP_URL=https://your-app.vercel.app
```

---

## 8. Чеклист

- [ ] `DATABASE_URL` — Postgres (не SQLite)
- [ ] `PUBLIC_BASE_URL` = Railway domain
- [ ] Volume `/data` + `TELETHON_SESSION_PATH`
- [ ] Telethon login в Shell
- [ ] `/api/health` → ok
- [ ] `/health` в боте → Telethon ✅, LLM ✅
- [ ] `LUMO_MODE=worker` на Railway
- [ ] На ПК не запущен `main.py` с polling одновременно

---

## 9. Обновление

```bash
git push origin main
```

Railway пересоберёт автоматически.

---

## 10. Troubleshooting

| Проблема | Решение |
|---------|---------|
| `database is locked` | SQLite на Railway — перейди на Postgres |
| Telethon ❌ | Volume + `telethon_login_qr.py` в Shell |
| Mini App пустой | Проверь `PUBLIC_BASE_URL`, открой `/app/` |
| Conflict polling | На Railway только `worker`, polling только `bot_main.py` |
| Supabase connection | URI pooler `:6543`, код уже настроен |

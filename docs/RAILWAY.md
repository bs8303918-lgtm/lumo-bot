# Деплой Lumo на Railway (Hobby)

Railway крутит **worker** 24/7: мониторинг каналов, LLM, **API**.  
**Mini App** — отдельно на **[Vercel](./VERCEL.md)**.  
**Telegram polling** — опционально на ПК через `bot_main.py`.

---

## Архитектура

```
Vercel          →  Mini App (React)
Railway         →  API /api/* + monitor + LLM
Supabase/Railway → PostgreSQL
Твой ПК         →  bot_main.py (polling, опционально)
```

> **Один токен бота = один polling.** На Railway только `LUMO_MODE=worker`.

---

## 1. GitHub

`https://github.com/bs8303918-lgtm/lumo-bot` → Railway: **Deploy from GitHub**

---

## 2. PostgreSQL

**Supabase** (free) или **Railway → Add PostgreSQL** → `DATABASE_URL`

---

## 3. Variables (Railway)

**Обязательные:**

```env
LUMO_MODE=worker
SERVE_MINI_APP=false
AUTO_BUILD_WEBAPP=false
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
TELEGRAM_WEBAPP_URL=https://YOUR-APP.vercel.app
API_CORS_ORIGINS=https://YOUR-APP.vercel.app
SKIP_INSTANCE_LOCK=true
TELETHON_SESSION_PATH=/data/lumo_session
```

Сначала задеploy Railway → скопируй domain в `PUBLIC_BASE_URL`.  
После деплоя Vercel → добавь URL в `TELEGRAM_WEBAPP_URL` и `API_CORS_ORIGINS` → redeploy Railway.

---

## 4. Volume для Telethon

Mount path: `/data`  
Variable: `TELETHON_SESSION_PATH=/data/lumo_session`

Shell:
```bash
python scripts/telethon_login_qr.py
```

---

## 5. Vercel (Mini App)

Полная инструкция: **[docs/VERCEL.md](./VERCEL.md)**

Кратко:
```env
VITE_API_URL=https://YOUR-SERVICE.up.railway.app
VITE_BASE_PATH=/
```

---

## 6. Бот на ПК

```env
LUMO_MODE=bot
DATABASE_URL=...тот же...
TELEGRAM_BOT_TOKEN=...тот же...
TELEGRAM_WEBAPP_URL=https://YOUR-APP.vercel.app
```

```powershell
python bot_main.py
```

---

## 7. Чеклист

- [ ] Railway `/api/health` → ok  
- [ ] Vercel Mini App открывается  
- [ ] `TELEGRAM_WEBAPP_URL` → Vercel  
- [ ] CORS: Vercel в `API_CORS_ORIGINS`  
- [ ] BotFather: домен Vercel  
- [ ] Telethon volume + login  
- [ ] `/health` в боте → Telethon ✅  

---

## 8. Troubleshooting

| Проблема | Решение |
|---------|---------|
| CORS | `API_CORS_ORIGINS` = Vercel URL |
| Open → старый /app | `TELEGRAM_WEBAPP_URL` на Vercel |
| Telethon ❌ | Volume + login в Shell |
| SQLite locked | Postgres, не SQLite |

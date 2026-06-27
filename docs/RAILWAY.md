# Деплой Lumo на Railway (Hobby)

На Railway работает **всё 24/7**:
- Telegram-бот (`/start`, кнопки, карточки)
- мониторинг каналов (Telethon)
- LLM
- API

**Mini App** — отдельно на **[Vercel](./VERCEL.md)**.

---

## Архитектура

```
Vercel           →  Mini App (React)
Railway          →  bot + API + monitor + LLM  (LUMO_MODE=full)
Supabase/Railway →  PostgreSQL
```

> **Не запускай** `main.py` или `bot_main.py` на ПК одновременно с Railway — один токен = один polling, будет конфликт.

---

## 1. GitHub

`https://github.com/bs8303918-lgtm/lumo-bot` → Railway: **Deploy from GitHub**

---

## 2. PostgreSQL (Supabase)

Railway = **долгоживущий контейнер** (не serverless). Подключение через Supabase:

### Какой режим выбрать в Supabase → Connect

| Режим | Порт | Для Lumo на Railway |
|-------|------|---------------------|
| **Transaction pooler** | **6543** | ✅ **Рекомендуем** — уже настроено в коде |
| Session pooler | 5432 | ✅ Тоже ок (если IPv4) |
| Direct connection | 5432 | ⚠️ Только если Railway видит IPv6 |

**Бери Transaction pooler (6543)** — самый простой вариант.

### Шаги

1. [supabase.com](https://supabase.com) → **New project** → запомни пароль БД  
2. **Connect** (или Settings → Database → Connection string)  
3. Вкладка **ORM** или **URI**  
4. Mode: **Transaction pooler**  
5. Скопируй строку вида:
   ```
   postgresql://postgres.xxxxx:[YOUR-PASSWORD]@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
   ```
6. Замени `[YOUR-PASSWORD]` на свой пароль  
7. Railway → сервис **lumo-bot** → **Variables** → New Variable:
   - Name: `DATABASE_URL`
   - Value: вставь URI **как есть** (код сам добавит `+asyncpg`)

> Не ставь кавычки вокруг URL. Если в пароле есть `@`, `#`, `%` — смени пароль в Supabase на простой.

8. **Redeploy** lumo-bot  
9. Supabase → **Table Editor** — после старта появятся таблицы `users`, `raw_messages`, …

### Или Railway Postgres (без Supabase)

1. Project → **+ New → Database → PostgreSQL**  
2. lumo-bot → Variables → **Add Reference** → `DATABASE_PRIVATE_URL`  
3. Redeploy  

Таблицы создаются автоматически при первом старте.

---

## 3. Variables (Railway → lumo-bot)

```env
LUMO_MODE=full
SERVE_MINI_APP=false
AUTO_BUILD_WEBAPP=false
DATABASE_URL=postgresql://...
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

| Переменная | Зачем |
|------------|--------|
| `LUMO_MODE=full` | бот + worker в одном процессе |
| `PUBLIC_BASE_URL` | домен Railway (API) |
| `TELEGRAM_WEBAPP_URL` | домен Vercel (кнопка Open) |
| `TELETHON_SESSION_PATH` | сессия Telethon на volume |

---

## 4. Volume для Telethon (обязательно)

Без volume сессия сотрётся при redeploy.

1. lumo-bot → **Volumes** → Mount path: `/data`  
2. Variable: `TELETHON_SESSION_PATH=/data/lumo_session`  
3. **Shell:**
   ```bash
   python scripts/telethon_login_qr.py
   ```
   QR → Telegram → Настройки → Устройства  

---

## 5. Vercel (Mini App)

См. **[docs/VERCEL.md](./VERCEL.md)**

```env
VITE_API_URL=https://YOUR-SERVICE.up.railway.app
VITE_BASE_PATH=/
```

После деплоя Vercel — обнови `TELEGRAM_WEBAPP_URL` и `API_CORS_ORIGINS` на Railway → **Redeploy**.

---

## 6. Проверка

| Проверка | Ожидание |
|----------|----------|
| `https://...railway.app/api/health` | `{"status":"ok"}` |
| Telegram `/ping` | бот отвечает |
| `/health` | Telethon ✅, LLM ✅ |
| Кнопка Open | открывает Vercel |
| Logs | `Start polling`, `Monitor cycle` |

---

## 7. Локально (только для разработки)

**Останови Railway-сервис** или используй **другой** test-бот, иначе конфликт polling.

```powershell
# .env локально
LUMO_MODE=full
DATABASE_URL=...та же Supabase...
```

```powershell
python main.py
```

---

## 8. Troubleshooting

| Проблема | Решение |
|---------|---------|
| Бот не отвечает | Logs Railway, `TELEGRAM_BOT_TOKEN` |
| Conflict polling | Выключи `main.py` на ПК |
| Telethon ❌ | Volume + `telethon_login_qr.py` |
| CORS в Mini App | `API_CORS_ORIGINS` = Vercel URL |
| database error | `DATABASE_URL` = Postgres, не SQLite |
| Lumo already running | Только один инстанс Railway (1 replica) |

# Mini App на Vercel + API на Railway

```
Telegram Open →  Vercel (React Mini App)
                      │  VITE_API_URL
                      ▼
                 Railway (FastAPI /api/*)
                      │
                 PostgreSQL (Supabase / Railway)
```

---

## 1. Railway (API + bot)

Переменные **дополнительно** к базовым из [RAILWAY.md](./RAILWAY.md):

```env
LUMO_MODE=full
SERVE_MINI_APP=false
AUTO_BUILD_WEBAPP=false
PUBLIC_BASE_URL=https://lumo-bot-production-9903.up.railway.app
TELEGRAM_WEBAPP_URL=https://lumo-bot.vercel.app
API_CORS_ORIGINS=https://lumo-bot.vercel.app,https://lumo-bot-*.vercel.app
```

- `PUBLIC_BASE_URL` — URL **Railway** (API), не Vercel  
- `TELEGRAM_WEBAPP_URL` — URL **Vercel** (кнопка Open в боте)  
- `SERVE_MINI_APP=false` — Railway **не** отдаёт `/app/`, только API  

Проверка: `https://ТВОЙ-RAILWAY.up.railway.app/api/health`

---

## 2. Vercel (Mini App)

### Импорт проекта

1. [vercel.com](https://vercel.com) → **Add New → Project**  
2. Import `bs8303918-lgtm/lumo-bot`  
3. **Root Directory:** оставь корень репо (используется `/vercel.json`)  
   — или укажи `telegram-site/frontend` и деплой из `frontend/vercel.json`

### Environment Variables (Production)

| Variable | Value |
|----------|--------|
| `VITE_API_URL` | `https://ТВОЙ-RAILWAY.up.railway.app` |
| `VITE_BASE_PATH` | `/` |

Deploy → получишь `https://lumo-bot.vercel.app` (или свой alias)

### Обнови Railway

```env
TELEGRAM_WEBAPP_URL=https://lumo-bot.vercel.app
API_CORS_ORIGINS=https://lumo-bot.vercel.app
```

Redeploy Railway (чтобы CORS и кнопка Open обновились).

---

## 3. BotFather — домен Mini App

1. [@BotFather](https://t.me/BotFather) → `/mybots` → твой бот  
2. **Bot Settings → Menu Button / Web App**  
3. Добавь домен Vercel: `lumo-bot.vercel.app`  

Без этого Telegram может блокировать открытие Mini App.

---

## 4. Локальная разработка

**Терминал 1 — API (или полный worker):**
```powershell
python main.py
```

**Терминал 2 — Mini App:**
```powershell
cd telegram-site\frontend
npm install
npm run dev
```

`.env.local` во frontend:
```env
VITE_API_URL=http://127.0.0.1:8000
VITE_BASE_PATH=/
```

Или локально всё в одном: `SERVE_MINI_APP=true`, `PUBLIC_BASE_URL` + build → `http://localhost:8000/app/`

---

## 5. Чеклист

- [ ] Railway: `SERVE_MINI_APP=false`, API health ok  
- [ ] Vercel: `VITE_API_URL` → Railway  
- [ ] Railway: `TELEGRAM_WEBAPP_URL` → Vercel  
- [ ] Railway: `API_CORS_ORIGINS` включает Vercel URL  
- [ ] BotFather: домен Vercel  
- [ ] В Telegram: синяя кнопка Open → Vercel, данные грузятся  

---

## 6. Troubleshooting

| Проблема | Решение |
|---------|---------|
| CORS error в Mini App | Добавь Vercel URL в `API_CORS_ORIGINS` на Railway |
| Open ведёт на Railway/app | Задай `TELEGRAM_WEBAPP_URL` на Vercel |
| Пустой экран на Vercel | Проверь `VITE_API_URL`, redeploy Vercel после смены env |
| 401 в Mini App | Открывай только из Telegram (нужен `initData`) |

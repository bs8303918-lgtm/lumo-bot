# Lumo Site (Vercel) + Bot API (Railway)

```
Браузер / Telegram  →  Vercel (сайт/frontend)
                           │  VITE_API_URL
                           ▼
                      Railway (main.py → api/app.py)
                           │
                      PostgreSQL (Supabase) — та же база, что у бота
```

Сайт **не** использует локальный `сайт/backend` и `lumo.db` в проде. Все запросы идут в **живой API бота** на Railway.

---

## 1. Railway (уже есть бот)

Добавь или обнови переменные:

```env
PUBLIC_BASE_URL=https://ТВОЙ-СЕРВИС.up.railway.app
API_CORS_ORIGINS=https://твой-сайт.vercel.app
TELEGRAM_WEBAPP_URL=https://твой-сайт.vercel.app
SERVE_MINI_APP=false
```

Проверка: `https://ТВОЙ-СЕРВИС.up.railway.app/api/health` → `"db": "ok"`

---

## 2. Vercel (Lumo-site репозиторий)

1. Import `bs8303918-lgtm/Lumo-site`
2. **Root Directory:** `.` (корень репо = frontend)
3. **Environment Variables:**

| Variable | Value |
|----------|--------|
| `VITE_API_URL` | `https://ТВОЙ-СЕРВИС.up.railway.app` |

4. Deploy

---

## 3. BotFather — домен для входа

Чтобы работала кнопка **Login with Telegram** на сайте:

1. [@BotFather](https://t.me/BotFather) → `/mybots` → @LumoAI1bot
2. **Bot Settings → Domain**
3. Укажи домен Vercel: `твой-сайт.vercel.app`

Без этого виджет входа не авторизует пользователей.

---

## 4. Как работает авторизация

| Способ | Когда |
|--------|--------|
| **Telegram Login Widget** | Пользователь на сайте в браузере — кнопка «Войти через Telegram» |
| **X-Telegram-Init-Data** | Сайт открыт как Mini App из Telegram |
| **X-Dev-Telegram-Id** | Только локально, если `API_ALLOW_DEV_AUTH=true` на Railway |

После входа сайт шлёт запросы с тем же аккаунтом, что и бот: лимиты, подписка, профиль — из **PostgreSQL**.

---

## 5. Локальная разработка

**Терминал 1 — полный бот + API:**

```powershell
cd C:\Users\User\Desktop\lumo-bot
python main.py
```

**Терминал 2 — сайт:**

```powershell
cd сайт\frontend
# .env.local:
# VITE_API_URL=http://127.0.0.1:8000
# API_ALLOW_DEV_AUTH=true на Railway не нужно локально — используй Login Widget или dev id
npm run dev
```

`vite.config.js` проксирует `/api` → `:8000`, если `VITE_API_URL` не задан.

---

## 6. Чеклист

- [ ] Railway: health ok, `DATABASE_URL` → Postgres
- [ ] Vercel: `VITE_API_URL` = домен Railway (без `/api`)
- [ ] Railway: `API_CORS_ORIGINS` включает Vercel URL
- [ ] BotFather: Domain = Vercel домен
- [ ] На сайте: войти через Telegram → запрос в чате → карточки из базы

---

## 7. Troubleshooting

| Проблема | Решение |
|---------|---------|
| CORS error | Добавь Vercel URL в `API_CORS_ORIGINS`, redeploy Railway |
| 401 Unauthorized | Войди через Telegram на сайте или открой из бота |
| HTML вместо JSON | Неверный `VITE_API_URL` — только origin Railway |
| Login Widget не работает | BotFather → Domain для Vercel |
| Пустой каталог | Проверь `DATABASE_URL` и `/api/health` |

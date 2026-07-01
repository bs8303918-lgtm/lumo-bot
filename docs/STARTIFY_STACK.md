# Lumo ↔ AI Startify — технологический стек

Документ для команды Startify: что где живёт и кто за что отвечает.

---

## Общая схема

```
┌─────────────────────┐         HTTPS (Partner API)         ┌──────────────────────┐
│  AI Startify        │  ─────────────────────────────────► │  Lumo                │
│  Next.js + NestJS   │  ◄─────────────────────────────────  │  FastAPI + aiogram   │
│  Prisma + Postgres  │         JSON + Bearer API key       │  SQLAlchemy + Supabase│
└─────────┬───────────┘                                     └──────────┬───────────┘
          │                                                              │
          │ Kaspi API / webhook                                            │ Telegram Bot API
          ▼                                                              ▼
   ┌─────────────┐                                              ┌─────────────────┐
   │ Kaspi Pay   │                                              │ Пользователь    │
   │ (счета)     │                                              │ Telegram        │
   └─────────────┘                                              └─────────────────┘
```

| Система | Стек | Роль |
|---------|------|------|
| **AI Startify** | Next.js 14+, NestJS, Prisma, PostgreSQL | Лендинг, checkout, Kaspi, webhooks оплаты, CRM подписок |
| **Lumo** | Python 3.12, FastAPI, aiogram 3, Telethon, Railway, Supabase Postgres | Telegram-бот, мониторинг каналов, AI-каталог, **источник правды по доступу в боте** |
| **Связь** | REST `Partner API v1` | Startify → Lumo: активация тарифа, атрибуция, синк каталога |

---

## Startify (ваша сторона)

| Слой | Технология | Задачи |
|------|------------|--------|
| Frontend | **Next.js** (App Router) | UTM-лендинги, выбор тарифа, Telegram Login Widget, редирект в бота |
| Backend | **NestJS** | Billing, Kaspi, webhooks, вызовы Lumo Partner API |
| ORM | **Prisma** | Модели подписок, заказов, платежей, атрибуции |
| БД | **PostgreSQL** | Своя Postgres (не Supabase Lumo) |
| Очереди (опц.) | BullMQ + Redis | Retry webhook Kaspi, async sync с Lumo |

### Env (Startify)

```env
DATABASE_URL=postgresql://...
LUMO_PARTNER_API_URL=https://lumo-bot-production-9903.up.railway.app/api/partner/v1
LUMO_PARTNER_API_KEY=<общий секрет с Lumo>
KASPI_MERCHANT_ID=...
KASPI_API_KEY=...
KASPI_WEBHOOK_SECRET=...
TELEGRAM_BOT_USERNAME=LumoAI1bot
NEXT_PUBLIC_TELEGRAM_BOT_URL=https://t.me/LumoAI1bot
```

---

## Lumo (наша сторона)

| Слой | Технология | Задачи |
|------|------------|--------|
| Bot | **aiogram 3** | /start, deep link, уведомления об истечении тарифа, сбор телефона Kaspi |
| API | **FastAPI** | Mini App REST + **Partner API** для Startify |
| Worker | **Telethon** | Чтение каналов, LLM, daily digest |
| БД | **Supabase PostgreSQL** | `users`: telegram_id, tariff, expires_at, kaspi_phone, UTM |

### Env (Lumo Railway)

```env
PARTNER_API_KEY=<тот же секрет>
SUBSCRIPTIONS_ENFORCED=false   # true после запуска оплаты
SUBSCRIPTION_PREVIEW_ENABLED=true
STARTIFY_CHECKOUT_URL=https://startify.example/kassa/lumo
KASPI_PAYMENT_PHONE=+7 775 499 8313
```

---

## Идентификаторы и тарифы

Единые `plan id` на обеих сторонах:

| plan id | Тип | Срок | Цена (₸) | AI/день |
|---------|-----|------|----------|---------|
| `freemium` | бесплатный | ∞ | 0 | 3 |
| `trial_7d` | пробный | 7 дней | 0 | без лимита |
| `plan_1m` | paid | 30 дней | 990 | без лимита |
| `plan_3m` | paid | 90 дней | 4 990 | без лимита |
| `plan_6m` | paid | 180 дней | 7 990 | без лимита |
| `plan_12m` | paid | 365 дней | 11 880 | без лимита |
| `unlimited` | paid | навсегда | 49 000 | без лимита |

**Primary key пользователя для интеграции:** `telegram_id` (int64).

---

## Deep link и UTM

Startify формирует ссылку на бота:

```
https://t.me/LumoAI1bot?start=sf_ref_<utm_campaign>[_<plan>]
```

Примеры:

| UTM / кампания | Deep link payload | Эффект в Lumo |
|----------------|-------------------|---------------|
| grants | `sf_ref_grants` | partner_source=startify, partner_ref=grants |
| home + trial | `sf_ref_home_trial_7d` | + trial 7 дней (после доработки Lumo) |
| pricing 6m | `sf_ref_pricing_plan_6m` | ref=pricing, pending plan 6m |

Формат парсера уже в Lumo: `services/subscription.py` → `parse_startify_payload()`.

---

## Что уже готово в Lumo

- [x] Поля БД: `telegram_id`, `tariff_plan`, `tariff_expires_at`, `kaspi_phone`, `partner_source`, `partner_ref`
- [x] Partner API: `GET/PUT user`, `POST attribution`, `GET catalog`
- [x] Deep link атрибуция на `/start`
- [x] Каталог тарифов и проверка `expires_at`
- [x] Mini App: экран тарифов (preview)

## Что делаем по фазам

| Фаза | Lumo | Startify |
|------|------|----------|
| 1 | Авто trial при `sf_*_trial_7d`, cron истечения, push в бот | Prisma schema, deep links на сайте |
| 2 | FSM: выбор тарифа + телефон Kaspi в боте | Checkout API, создание счёта Kaspi |
| 3 | Webhook Lumo→Startify «новый user» | Webhook Kaspi→NestJS→`PUT /subscription` |
| 4 | `SUBSCRIPTIONS_ENFORCED=true` | Аналитика, админка заказов |

Подробные потоки, Prisma schema и тексты — в [STARTIFY_INTEGRATION.md](./STARTIFY_INTEGRATION.md).

API reference — [STARTIFY_API.md](./STARTIFY_API.md).

Промпт для Claude (развёртывание у Startify) — [STARTIFY_CLAUDE_DEPLOY_PROMPT.md](./STARTIFY_CLAUDE_DEPLOY_PROMPT.md).

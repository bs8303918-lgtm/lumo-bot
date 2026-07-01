# Промпт для Claude — развёртывание биллинга Lumo × AI Startify

Скопируй блок ниже **целиком** в Claude (или Cursor) в репозитории **AI Startify** (Next.js + NestJS + Prisma + PostgreSQL).

---

## PROMPT (copy from here)

```
Ты — senior full-stack инженер. Разверни интеграцию подписок Lumo × AI Startify в нашем монорепо.

## Контекст

Lumo — Telegram-бот (Python, Railway). У них уже есть Partner API v1.
Мы — AI Startify: Next.js (frontend) + NestJS (backend) + Prisma + PostgreSQL.

Бизнес-поток:
1. Пользователь с лендинга Startify (UTM) переходит в бота по deep link.
2. Lumo сохраняет telegram_id, UTM/ref, тариф (freemium или trial 7d) и дату окончания.
3. По истечении срока Lumo шлёт push в Telegram (их сторона); мы дублируем checkout на сайте.
4. Пользователь выбирает платный тариф (3/6/12 мес, безлимит) и вводит телефон Kaspi.
5. NestJS выставляет счёт Kaspi на сумму тарифа.
6. После webhook оплаты Kaspi → NestJS вызывает Lumo Partner API → доступ по telegram_id.

## Стек (строго)

- Frontend: Next.js 14+ App Router, TypeScript
- Backend: NestJS, TypeScript
- ORM: Prisma
- DB: PostgreSQL
- HTTP client: @nestjs/axios или fetch
- Валидация: class-validator
- Env: @nestjs/config

## Lumo Partner API (уже работает)

Base URL: process.env.LUMO_PARTNER_API_URL
  production: https://lumo-bot-production-9903.up.railway.app/api/partner/v1

Auth: Authorization: Bearer ${LUMO_PARTNER_API_KEY}

**Partner key (общий с Lumo Railway — скопируй в .env Startify):**
```
lumo_partner_I_xakIY1cpbkT_UNYar6yyHa0i-CBN40WpAo_Z9ALBE
```
Lumo Railway: переменная `PARTNER_API_KEY` — то же значение.

Endpoints:
- GET  /health
- GET  /users/{telegramId}
- PUT  /users/{telegramId}/subscription  ← после оплаты Kaspi
- POST /users/{telegramId}/attribution
- GET  /catalog/opportunities?limit=50&offset=0

PUT /users/{telegramId}/subscription body:
{
  "tariffPlan": "plan_6m",
  "kaspiPhone": "+77001234567",
  "partnerRef": "grants",
  "partnerSource": "startify",
  "expiresAt": "optional ISO8601"
}

Допустимые tariffPlan:
freemium | trial_7d | plan_1m | plan_3m | plan_6m | plan_12m | unlimited

Цены KZT:
- plan_1m: 990
- plan_3m: 4990
- plan_6m: 7990
- plan_12m: 11880
- unlimited: 49000

## Deep link для Next.js

Формат: https://t.me/LumoAI1bot?start=sf_ref_{utmCampaign}_{plan}

Примеры:
- sf_ref_grants_trial_7d  → trial 7 дней, ref=grants
- sf_ref_pricing_plan_6m  → ref=pricing, pending 6m

Реализуй lib/lumo-deeplink.ts и используй на лендингах.

## Prisma models (создай migration)

- LumoUser (telegramId BigInt unique, partnerRef, utm*, currentPlan, expiresAt, kaspiPhone)
- PaymentOrder (telegramId, tariffPlan, amountKzt, kaspiPhone, kaspiInvoiceId, status enum)
- KaspiWebhookEvent (payload Json, processed)
- AttributionEvent (utm + deepLinkPayload)

PaymentStatus: pending | invoice_sent | paid | failed | expired | refunded

## NestJS modules

1. lumo/lumo.module.ts + lumo.client.ts — typed client Partner API
2. billing/billing.service.ts:
   - createCheckout(dto): validate plan, create PaymentOrder, call Kaspi API (stub interface IKaspiClient if keys missing)
   - handleKaspiWebhook(payload): idempotent, on success → lumoClient.activateSubscription()
3. billing/billing.controller.ts:
   - POST /api/billing/checkout  { telegramId, tariffPlan, kaspiPhone, partnerRef? }
   - GET  /api/billing/orders/:id
4. kaspi/kaspi.webhook.controller.ts — POST /api/webhooks/kaspi (verify signature placeholder)

## Next.js pages

1. /lumo — лендинг с UTM query params → кнопка deep link в бота
2. /lumo/checkout — Telegram Login Widget → форма тариф + телефон Kaspi → POST NestJS checkout
3. /lumo/success — «счёт выставлен, проверьте Kaspi»

## Telegram Login Widget

Верифицируй hash по официальной документации Telegram.
Из виджета получай id → это telegramId для checkout.

## Тексты UI (RU)

Checkout title: «Оплата Lumo через Kaspi»
Phone label: «Номер телефона Kaspi (+7…)»
Success: «Счёт на {amount} ₸ выставлен. Откройте Kaspi и оплатите. Доступ в боте откроется автоматически.»

Kaspi invoice description template:
«AI Startify — Lumo {planLabel}»

## Env template (.env.example)

DATABASE_URL=
LUMO_PARTNER_API_URL=https://lumo-bot-production-9903.up.railway.app/api/partner/v1
LUMO_PARTNER_API_KEY=lumo_partner_I_xakIY1cpbkT_UNYar6yyHa0i-CBN40WpAo_Z9ALBE
KASPI_API_URL=
KASPI_MERCHANT_ID=
KASPI_API_KEY=
KASPI_WEBHOOK_SECRET=
TELEGRAM_BOT_TOKEN=  # для Login Widget verification if needed
NEXT_PUBLIC_TELEGRAM_BOT_USERNAME=LumoAI1bot

## Требования к качеству

- Idempotent webhook (same kaspi event id → no double activate)
- Retry Lumo PUT 3 times with exponential backoff on 5xx
- Log lumoSyncedAt on PaymentOrder
- Unit test: lumo.client activateSubscription mock
- E2E stub: checkout → fake webhook → assert PUT called

## Не делай

- Не храни LUMO_PARTNER_API_KEY во frontend
- Не дублируй AI/LLM Lumo — только биллинг и sync
- Не меняй контракт Lumo API без согласования

## Deliverables

1. prisma/schema.prisma + migration
2. NestJS modules (lumo, billing, kaspi webhook)
3. Next.js pages + deeplink helper
4. README-LUMO-INTEGRATION.md с командами deploy и test curl
5. curl examples для PUT subscription и POST checkout

Начни с Prisma schema и lumo.client.ts, затем billing flow, затем Next.js checkout.
```

---

## END PROMPT

---

## После генерации кода — smoke test

```bash
# 1. Health Lumo
export LUMO_PARTNER_API_URL=https://lumo-bot-production-9903.up.railway.app/api/partner/v1
export LUMO_PARTNER_API_KEY=lumo_partner_I_xakIY1cpbkT_UNYar6yyHa0i-CBN40WpAo_Z9ALBE
curl -s -H "Authorization: Bearer $LUMO_PARTNER_API_KEY" \
  "$LUMO_PARTNER_API_URL/health"

# 2. Тест активации (test telegram id)
curl -s -X PUT \
  -H "Authorization: Bearer $LUMO_PARTNER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"tariffPlan":"trial_7d","partnerRef":"smoke_test","partnerSource":"startify"}' \
  "$LUMO_PARTNER_API_URL/users/999999999/subscription"

# 3. Checkout (локальный NestJS)
curl -s -X POST http://localhost:3001/api/billing/checkout \
  -H "Content-Type: application/json" \
  -d '{"telegramId":999999999,"tariffPlan":"plan_3m","kaspiPhone":"+77001234567"}'
```

---

## Документы Lumo для команды

| Файл | Содержание |
|------|------------|
| [STARTIFY_STACK.md](./STARTIFY_STACK.md) | Стек и зоны ответственности |
| [STARTIFY_INTEGRATION.md](./STARTIFY_INTEGRATION.md) | Потоки, Prisma, тексты, webhooks |
| [STARTIFY_API.md](./STARTIFY_API.md) | Краткий API reference |

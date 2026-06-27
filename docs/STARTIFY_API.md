# Интеграция Lumo ↔ AI Startify

Lumo (Railway, FastAPI + бот) ↔ Startify (Next.js + NestJS + Prisma + Postgres).

## Сейчас (подготовка)

| Параметр | Значение |
|----------|----------|
| `SUBSCRIPTIONS_ENFORCED` | `false` — бот **не платный**, 3 AI-запроса/день |
| `SUBSCRIPTION_PREVIEW_ENABLED` | `true` — тарифы видны в Mini App → Профиль |
| `PARTNER_API_KEY` | секрет для server-to-server вызовов из NestJS |

Когда запустите оплату: `SUBSCRIPTIONS_ENFORCED=true` на Railway.

---

## Архитектура

**Каталог на сайте Startify** — NestJS забирает JSON из Lumo (`GET /catalog/opportunities`) и пишет в Postgres через Prisma (без AI на их стороне).

**Доступ к боту** — после оплаты Kaspi NestJS вызывает `PUT .../subscription` с `telegramId` и тарифом.

**Deep link:** `https://t.me/LumoAI1bot?start=sf_ref_home` — UTM в Lumo.

---

## Авторизация

```http
Authorization: Bearer <PARTNER_API_KEY>
```

Base URL: `https://lumo-bot-production-9903.up.railway.app/api/partner/v1`

---

## Endpoints

### `GET /health`

### `GET /users/{telegramId}`

Статус подписки и атрибуция.

### `PUT /users/{telegramId}/subscription`

После оплаты Kaspi:

```json
{
  "tariffPlan": "plan_3m",
  "kaspiPhone": "+77001234567",
  "partnerRef": "home",
  "partnerSource": "startify"
}
```

Тарифы: `freemium` | `trial_7d` | `plan_3m` | `plan_6m` | `plan_12m` | `unlimited`

### `POST /users/{telegramId}/attribution`

```json
{ "partnerSource": "startify", "partnerRef": "landing_grants" }
```

### `GET /catalog/opportunities?limit=50&offset=0`

Экспорт каталога для синка в Prisma.

---

## NestJS — после оплаты

```typescript
await fetch(`${LUMO_API}/users/${telegramId}/subscription`, {
  method: 'PUT',
  headers: {
    Authorization: `Bearer ${PARTNER_API_KEY}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    tariffPlan: 'plan_6m',
    kaspiPhone: phone,
    partnerSource: 'startify',
  }),
});
```

---

## Railway (Lumo)

```env
PARTNER_API_KEY=<секрет>
SUBSCRIPTIONS_ENFORCED=false
SUBSCRIPTION_PREVIEW_ENABLED=true
STARTIFY_CHECKOUT_URL=https://their-site.example/checkout
```

Полное описание — в этом файле в репозитории.

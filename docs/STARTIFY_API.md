# Интеграция Lumo ↔ AI Startify

Lumo (Railway, FastAPI + бот) ↔ Startify (Next.js + NestJS + Prisma + Postgres).

**Полная документация:**

| Документ | Содержание |
|----------|------------|
| [STARTIFY_STACK.md](./STARTIFY_STACK.md) | Стек Next/Nest/Prisma, env, тарифы |
| [STARTIFY_INTEGRATION.md](./STARTIFY_INTEGRATION.md) | UTM → бот → countdown → Kaspi → доступ |
| [STARTIFY_CATALOG_WEBHOOK.md](./STARTIFY_CATALOG_WEBHOOK.md) | Push конкурсов Lumo → Startify |
| [STARTIFY_CLAUDE_DEPLOY_PROMPT.md](./STARTIFY_CLAUDE_DEPLOY_PROMPT.md) | Промпт для Claude в репо Startify |

## Модель доступа в Mini App

| Функция | Доступ |
|---------|--------|
| Каталог, фильтры, карточки конкурсов | **Бесплатно всем**, без ограничений |
| AI-поиск (`/lumo/match`, `/users/interest`) | **Платно** — freemium получает `AI_SEARCH_DAILY_LIMIT` попыток в день (сейчас `1`), дальше — оффер подписки |

## Сейчас (прод, Railway)

| Параметр | Значение |
|----------|----------|
| `SUBSCRIPTIONS_ENFORCED` | `true` — лимит AI-поиска включён, freemium ограничен `AI_SEARCH_DAILY_LIMIT`/день |
| `SUBSCRIPTION_PREVIEW_ENABLED` | `true` — тарифы видны в Mini App → Профиль |
| `AI_SEARCH_DAILY_LIMIT` | `1` — бесплатных AI-поисков в день для freemium |
| `PARTNER_API_KEY` | секрет для server-to-server вызовов из NestJS |

---

## Архитектура

**Каталог на сайте Startify** — два способа:

1. **Push (рекомендуется):** Lumo шлёт `POST` на `STARTIFY_CATALOG_WEBHOOK_URL` при каждом новом конкурсе.
2. **Pull (fallback):** NestJS cron → `GET /catalog/opportunities` → Prisma.

Подробно: [STARTIFY_CATALOG_WEBHOOK.md](./STARTIFY_CATALOG_WEBHOOK.md)

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

Экспорт каталога для синка в Prisma. Не требует оплаты — каталог открыт всем.

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
SUBSCRIPTIONS_ENFORCED=true
SUBSCRIPTION_PREVIEW_ENABLED=true
AI_SEARCH_DAILY_LIMIT=1
STARTIFY_CHECKOUT_URL=https://their-site.example/checkout
```

Полное описание — в этом файле в репозитории.

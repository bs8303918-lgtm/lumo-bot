# AI Startify ↔ Lumo integration (Rev 1.0 · 2026-07-13)

Официальный гайд Startify: `lumo-integration-guide.md`.

---

## Что уже есть в Lumo

| Компонент | Статус |
|-----------|--------|
| Partner billing API `PUT /api/partner/v1/users/{telegramId}/subscription` | ✅ |
| Partner catalog export `GET /api/partner/v1/catalog/opportunities` | ✅ |
| Catalog push webhook → Startify | ✅ `services/startify_catalog_push.py` |
| Events: created / updated / deactivated | ✅ |
| Seed script | ✅ `scripts/push_catalog_to_startify.py` |
| Smoke test | ✅ `scripts/smoke_startify_catalog.py` |
| Admin `/push_startify` | ✅ |

---

## Railway Variables (обязательно)

```env
PARTNER_API_KEY=<тот же Bearer, что у Startify>
STARTIFY_CATALOG_PUSH_ENABLED=true

# Prod
STARTIFY_CATALOG_WEBHOOK_URL=https://api.aistartify.com/api/webhooks/lumo/catalog

# или Dev
# STARTIFY_CATALOG_WEBHOOK_URL=https://api-dev.aistartify.com/api/webhooks/lumo/catalog
```

Ключ **не коммить** в код (только в Railway / `.env` локально).

После смены Variables → **Redeploy**.

---

## Auth (Lumo → Startify)

```
Authorization: Bearer <PARTNER_API_KEY>
Content-Type: application/json
```

## Billing (Startify → Lumo)

```
PUT https://lumo-bot-production-9903.up.railway.app/api/partner/v1/users/{telegramId}/subscription
Authorization: Bearer <PARTNER_API_KEY>
```

Body (пример):

```json
{
  "tariffPlan": "plan_3m",
  "expiresAt": null,
  "partnerSource": "startify",
  "partnerRef": "kaspi_order_123"
}
```

---

## Catalog webhook payload

```json
{
  "event": "opportunity.created",
  "sentAt": "2026-07-13T10:00:00Z",
  "source": "lumo-catalog",
  "opportunity": {
    "id": 123,
    "type": "grant",
    "title": "…",
    "description": "…",
    "deadline": "15 августа 2026",
    "applicationUrl": "https://…",
    "messageLink": "https://t.me/…",
    "emoji": "🏆",
    "label": "Гранты",
    "tags": ["KZ"],
    "isPremium": false,
    "isActive": true
  }
}
```

`type` ∈ `grant` | `internship` | `event` (маппинг из русских типов Lumo).

Retries на 5xx: 0.5s → 1s → 2s. На 4xx — без ретрая.

---

## Автоматическая отправка (без ручного /push_startify)

1. **Сразу** — когда мониторинг + LLM добавляют новый конкурс → `opportunity.created`
2. **При снятии** — expired / дубликаты → `opportunity.deactivated`
3. **Каждые 6 часов** — полный бэкап-синк активных → `opportunity.updated`

Нужны Railway Variables (`PARTNER_API_KEY` + `STARTIFY_CATALOG_WEBHOOK_URL`) и рабочий webhook у Startify (не 404).

---

## Чеклист

1. [ ] Railway: `PARTNER_API_KEY` + `STARTIFY_CATALOG_WEBHOOK_URL` (prod)
2. [ ] Redeploy Railway
3. [ ] Smoke: `python scripts/smoke_startify_catalog.py` → `{"ok":true}`
4. [ ] Seed: `python scripts/push_catalog_to_startify.py` (или `/push_startify` в боте)
5. [ ] Проверить карточку на сайте Startify
6. [ ] Startify дергает billing PUT после Kaspi — тариф появляется у пользователя

---

## Команды

```bash
# health Startify
curl -s https://api.aistartify.com/health

# smoke create+deactivate
python scripts/smoke_startify_catalog.py

# seed all active (opportunity.created)
python scripts/push_catalog_to_startify.py

# re-sync as updates
python scripts/push_catalog_to_startify.py --updated
```

В боте (админ): `/push_startify` · `/push_startify 1234`

# AI Startify Grants — Lumo Partner Integration Guide

**Rev 1.0 · 2026-07-13**

---

## Auth

Все запросы от Lumo к AI Startify должны содержать заголовок:

```
Authorization: Bearer <PARTNER_API_KEY>
```

Храни ключ как Railway secret-переменную. Не коммить в код.

---

## Catalog Webhook

### Endpoint

| | |
|---|---|
| **Dev** | `POST https://api-dev.aistartify.com/api/webhooks/lumo/catalog` |
| **Prod** | `POST https://api.aistartify.com/api/webhooks/lumo/catalog` |
| **Content-Type** | `application/json` |

Отправляй при любом изменении в каталоге. Мы делаем upsert по `opportunity.id`.

### Типы событий

| event | Что происходит |
|---|---|
| `opportunity.created` | Новая запись — вставляем |
| `opportunity.updated` | Изменилось что-то — обновляем все поля |
| `opportunity.deactivated` | Снимаем с публикации (`isActive = false`) |

### Структура запроса

```json
{
  "event":   "opportunity.created",
  "sentAt":  "2026-07-13T10:00:00Z",
  "source":  "lumo-catalog",
  "opportunity": {
    "id":                123,
    "type":              "grant",
    "title":             "Грант Nazarbayev University 2026",
    "description":       "До 5 млн ₸ на tech-стартапы в сфере AgriTech и CleanEnergy",
    "deadline":          "15 августа 2026",
    "requirements":      "Команда 2+ чел., MVP, резиденты Казахстана",
    "applicationUrl":    "https://nu.edu.kz/grant",
    "messageLink":       "https://t.me/lumo_grants/42",
    "sourceChannelName": "lumo_grants",
    "emoji":             "🏆",
    "label":             "AgriTech",
    "tags":              ["AgriTech", "KZ", "2026"],
    "isPremium":         false,
    "isActive":          true
  }
}
```

### Поля opportunity

| Поле | Тип | | Описание |
|---|---|---|---|
| `id` | integer | **required** | Твой внутренний ID. По нему делаем upsert. |
| `type` | string | **required** | `"grant"` / `"internship"` / `"event"`. Определяет вкладку на странице. |
| `title` | string | **required** | Короткий заголовок, до 80 символов. |
| `description` | string | **required** | Полное описание. |
| `deadline` | string | **required** | Читаемый текст, напр. `"15 августа 2026"`. |
| `applicationUrl` | string\|null | optional | Ссылка на сайт гранта/стажировки. **Основная кнопка →** |
| `messageLink` | string\|null | optional | Ссылка на пост в Telegram-канале. Fallback если нет `applicationUrl`. |
| `emoji` | string\|null | optional | Один эмодзи для иконки карточки. |
| `tags` | string[] | optional | Теги отрасли/темы. Показываются как чипы. |
| `isPremium` | boolean | optional | `true` → карточка размыта, CTA «Подписаться». По умолчанию `false`. |
| `isActive` | boolean | optional | `false` → скрываем. По умолчанию `true`. |
| `requirements` | string\|null | optional | Требования/условия участия. |
| `label` | string\|null | optional | Короткий лейбл-категория. |
| `sourceChannelName` | string\|null | optional | Для атрибуции. |

> **Важно по кнопке →:** отправляй хотя бы одно из двух — `applicationUrl` или `messageLink`. Если оба `null` — кнопки не будет.

### Ответы

| Статус | Body | Значение |
|---|---|---|
| `200 OK` | `{"ok":true}` | Успешно |
| `400 Bad Request` | `{"message":"..."}` | Ошибка валидации — проверь типы полей |
| `401 Unauthorized` | `{"message":"Invalid Lumo webhook token"}` | Неверный или отсутствующий `Authorization` |
| `500 Internal Server Error` | `{"message":"..."}` | Повтори с backoff |

При 5xx: ретрай 3 раза с задержкой 500ms → 1s → 2s. При 4xx не ретраить.

---

## Smoke Tests

### Создать запись

```bash
curl -sX POST https://api-dev.aistartify.com/api/webhooks/lumo/catalog \
  -H "Authorization: Bearer <PARTNER_API_KEY> \
  -H "Content-Type: application/json" \
  -d '{
    "event": "opportunity.created",
    "sentAt": "2026-07-13T12:00:00Z",
    "source": "lumo-catalog",
    "opportunity": {
      "id": 1,
      "type": "grant",
      "title": "Test Grant",
      "description": "Test description",
      "deadline": "31 декабря 2026",
      "applicationUrl": "https://example.com",
      "emoji": "🏆",
      "tags": ["test"],
      "isPremium": false,
      "isActive": true
    }
  }'

# Ожидается: {"ok":true}
```

### Деактивировать

```bash
curl -sX POST https://api-dev.aistartify.com/api/webhooks/lumo/catalog \
  -H "Authorization: Bearer <PARTNER_API_KEY> \
  -H "Content-Type: application/json" \
  -d '{
    "event": "opportunity.deactivated",
    "sentAt": "2026-07-13T12:01:00Z",
    "source": "lumo-catalog",
    "opportunity": { "id": 1 }
  }'

# Ожидается: {"ok":true}
```

---

## Billing API (мы вызываем тебя)

Когда пользователь оплачивает через Kaspi, мы активируем его подписку вызовом вашего partner API. Действий с твоей стороны не нужно — просто держи эндпоинт доступным.

```
PUT https://lumo-bot-production-9903.up.railway.app/api/partner/v1/users/{telegramId}/subscription
Authorization: Bearer <PARTNER_API_KEY>
```

Ключ уже добавлен в наши K8s-секреты на dev и prod (выполнено 2026-07-13).

---

## Чеклист для Lumo

- [ ] Добавить в Railway (dev): `STARTIFY_CATALOG_WEBHOOK_URL=https://api-dev.aistartify.com/api/webhooks/lumo/catalog`
- [ ] Добавить в Railway (prod): `STARTIFY_CATALOG_WEBHOOK_URL=https://api.aistartify.com/api/webhooks/lumo/catalog`
- [ ] Bearer key хранить как Railway secret (не хардкодить)
- [ ] Отправить `opportunity.created` для всех существующих активных записей (первоначальный seed нашей БД)
- [ ] Подключить `opportunity.updated` и `opportunity.deactivated` для будущих изменений
- [ ] Убедиться, что у каждой записи есть `applicationUrl` или `messageLink`
- [ ] Прогнать smoke test, убедиться что возвращает `{"ok":true}`

---

## Контакты

| | |
|---|---|
| Dev API | `https://api-dev.aistartify.com` |
| Prod API | `https://api.aistartify.com` |
| Health check | `GET /health` → `{"status":"ok"}` |

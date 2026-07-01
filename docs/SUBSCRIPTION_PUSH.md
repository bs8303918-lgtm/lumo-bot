# Push-расписание подписки Lumo (Startify trial)

Автоматические сообщения в Telegram после перехода с AI Startify.

## Trial при /start

Любая ссылка `https://t.me/LumoAI1bot?start=sf_*` (кроме явного платного тарифа в payload):

- выдаётся `trial_7d`
- `tariff_expires_at = now + 7 days`
- один раз на пользователя (повтор — только если в ссылке снова `trial_7d`)

Примеры:

| Ссылка | Trial |
|--------|-------|
| `sf_ref_grants` | ✅ 7 дней |
| `sf_ref_home_trial_7d` | ✅ 7 дней |
| `sf_ref_pricing_plan_6m` | ❌ (ожидается оплата 6m) |

## Push-расписание (Duolingo-style)

Worker: `subscription_reminders` — проверка **каждый час** (`SUBSCRIPTION_REMINDER_INTERVAL_SECONDS=3600`).

| Ключ | Когда | Смысл |
|------|-------|--------|
| `remind_3d` | за ~3 дня до конца trial | «Осталось 3 дня», безлимит 49k, все тарифы |
| `remind_1d` | за ~1 день | «Завтра конец», акцент 6 мес / безлимит |
| `expired` | 0–6 ч после конца trial | «Trial завершён», freemium 3 AI/день |
| `winback_3d` | +3 дня после конца | «Скучаем», если не купил |
| `winback_7d` | +7 дней после конца | последнее напоминание |

Каждое сообщение — **один раз** (флаг в `system_state`: `sub_push:{user_id}:{kind}`).

Кнопки: `STARTIFY_CHECKOUT_URL` + Mini App (если заданы).

## Тексты

Исходники: `bot/texts/subscription_push.py`

## События аналитики

- `subscription_trial_granted`
- `subscription_remind_3d` / `subscription_remind_1d`
- `subscription_trial_expired`
- `subscription_winback_3d` / `subscription_winback_7d`

## Админ: счётчики

Telegram (только admin): **`/subs`**

Показывает: купили / trial / Startify / разбивка по тарифам.

Mini App admin API: `GET /api/admin/tracking` → поле `subscriptions`.

## Env

```env
STARTIFY_CHECKOUT_URL=https://startify.example/lumo/checkout
SUBSCRIPTION_REMINDER_INTERVAL_SECONDS=3600
```

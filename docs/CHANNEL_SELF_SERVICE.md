# Self-service добавление Telegram-каналов — ТЗ

Расширение органического роста базы каналов силами пользователей вместо
ручного seed-листа команды. Документ описывает целевую архитектуру,
опирается на уже существующий флоу `/add_channel` и указывает, что в нём
нужно доработать, а что можно переиспользовать as-is.

## 0. Что уже есть в коде (baseline)

Прежде чем проектировать фичу с нуля, важно зафиксировать: часть требований
уже реализована.

| Требование из ТЗ | Статус | Где |
|---|---|---|
| Приём ссылки/username от пользователя | ✅ есть | `bot/handlers/channels.py::cmd_add_channel`, `process_channel_input` |
| Нормализация `t.me/name`, `@name`, `https://t.me/name` → 1 ID | ✅ есть | `db/repositories/users.py::normalize_channel_identifier` |
| Проверка «публичный ли канал» | ✅ есть (базово) | `monitor/channel_resolver.py::ChannelResolver.validate_public_channel` — резолвит через Telethon, отсекает приватные/несуществующие/не-каналы, требует `username` |
| Дедупликация на уровне БД (общий канал = 1 запись, N подписчиков) | ✅ есть | `MonitoredChannel` — общая таблица источников, `UserChannel` — подписка юзера; `_ensure_monitored()` делает upsert + `source_count += 1` |
| Динамическое добавление канала в мониторинг без рестарта | ✅ есть | `MonitorWorker.scan_channel()` вызывается синхронно сразу после `add_user_channel()` |
| Лимит каналов на пользователя | ⚠️ частично | `max_user_channels=5` — это **общий потолок** («не больше 5 каналов одновременно»), не **дневной rate-limit** («не больше 5 в день») |
| AI-классификатор релевантности канала | ❌ нет | Сейчас проверяется только «это публичный Telegram-канал», не «это канал про конкурсы/гранты» |
| Порог активности (не пустой/не заброшенный) | ❌ нет | Пустой канал не считается ошибкой (курсор просто ставится в 0), но это не сообщается пользователю как повод отклонить |
| `status: pending/verified/rejected`, `quality_score` | ❌ нет | Канал становится «живым» источником немедленно после прохождения `validate_public_channel` |
| Явное согласie на публичность (общая база vs приватно) | ❌ нет | Любой добавленный канал сразу становится общим источником для всех пользователей Lumo (через `source_count`), без явного предупреждения |
| Геймификация («канал принёс X конкурсов») | ❌ нет | — |

Вывод: базовый pipeline «добавить → зарезолвить → мониторить» уже
работает и дедупликация уже решена архитектурно. Основной объём работы —
**слой верификации/скоринга/приватности/модерации поверх существующего
`MonitoredChannel`**, а не переписывание системы с нуля.

---

## 1. UX-флоу

```
Пользователь: /add_channel
  → бот: "Пришли @username или ссылку"
Пользователь: @some_channel
  → нормализация identifier
  → rate-limit check (≤5 добавлений/24ч на пользователя)
  → если превышен → "Ты уже добавил 5 каналов сегодня, попробуй завтра"
  → dedup check по MonitoredChannel.channel_identifier
      ├─ канал уже verified в базе
      │     → просто создать UserChannel (подписка), без повторной верификации
      │     → "✅ Канал уже в базе Lumo, подписал тебя на него"
      ├─ канал уже pending (кто-то другой уже отправил на проверку)
      │     → создать UserChannel сразу (не ждать вручную) либо предложить
      │       дождаться проверки — см. §3, решение: подписываем сразу,
      │       статус проверки не блокирует личную подписку
      │     → "🕓 Канал уже проверяется, подписал тебя — как только пройдёт
      │        проверку, начнём получать из него посты"
      ├─ канал уже rejected (ранее отклонён)
      │     → "❌ Этот канал не подошёл под тематику Lumo: <причина>"
      │       (без возможности повторной отправки того же identifier чаще
      │       чем раз в N дней — защита от повторного спама одним и тем же
      │       каналом)
      └─ канал новый
            → ChannelResolver.validate_public_channel() (как сейчас)
                ├─ не паблик / не найден / приватный → отказ с причиной (как сейчас)
                └─ ок → запрос согласия на приватность (см. §4)
                      → активность + AI-классификатор (см. §3)
                      → quality_score
                      → решение: verified (авто) / pending (на ручной approve) / rejected
                      → создать MonitoredChannel(status=...) + UserChannel (подписка)
                      → если verified → backfill истории через существующий pipeline (см. §6)
                      → ответ пользователю со статусом + гейм-плашка (см. §7)
```

Финальные статусы, которые видит пользователь (п.1 требований):
`добавлен и проверяется` / `уже в базе` / `не подходит (причина)`.

### 1.1 Хендлеры бота (aiogram Router, `bot/handlers/channels.py`)

Существующие, дорабатываются:

- `Command("add_channel")` → `cmd_add_channel`
  - добавить проверку rate-limit (5/24ч) **до** входа в FSM
- `StateFilter(AddChannelStates.waiting_for_channel)` → `process_channel_input`
  - расширяется по схеме §1: dedup по трём статусам, вызов классификатора,
    вызов privacy-шага

Новые:

- `CallbackQuery.data.startswith("channel_privacy:")` → `process_privacy_choice`
  - callback_data: `channel_privacy:{shared|private}:{pending_submission_token}`
  - завершает добавление канала после ответа на вопрос о приватности
- `Command("my_channels")` → `cmd_my_channels` (уже есть, дополняется)
  - добавить блок геймификации: «Твой канал @x принёс N конкурсов»
- Админские (`bot/handlers/admin.py`, за `AdminFilter()`):
  - `Command("channel_queue")` → список каналов со `status=pending`,
    `quality_score`, кто добавил, краткая сводка последних постов
  - `CallbackQuery.data.startswith("channel_review:")` →
    `channel_review:approve:{monitored_channel_id}` /
    `channel_review:reject:{monitored_channel_id}:{reason_code}`
    — ручной approve/reject (MVP без авто-верификации, см. §8)

Новое FSM-состояние (`bot/states.py`):

```python
class AddChannelStates(StatesGroup):
    waiting_for_channel = State()
    waiting_for_privacy_choice = State()  # новое
```

---

## 2. Дедупликация

Уже решено архитектурно и remains as-is:

- `normalize_channel_identifier()` схлопывает `@name`, `t.me/name`,
  `https://t.me/name`, `telegram.me/name` → `name` (lowercase).
- `MonitoredChannel.channel_identifier` — `unique=True, index=True`.
- `ChannelRepository._ensure_monitored()` — upsert: если канал уже
  существует, инкрементит `source_count`, не создаёт вторую запись.
- `UserChannel` — единственное, что размножается на пользователя
  (`UniqueConstraint(user_id, channel_identifier)`), сам источник (посты,
  каталог) — общий.

Единственное дополнение: в `_ensure_monitored()` при первом создании
записи нужно передавать `status="pending"` вместо мгновенного «живого»
источника (сейчас туда сразу летит first-scan). Технически это не
дублирование, а смена момента, когда канал становится «мониторимым».

---

## 3. Верификация и скоринг качества

### 3.1 Активность (не пустой / не заброшенный)

Дешёвая проверка, не требует LLM — уже есть сырые данные из
`client.get_messages(entity, limit=N)`, которые и так забираются при
first-scan (`monitor/worker.py::_process_channel`, ветка `is_first_scan`).

```
activity_ok, activity_reason = check_activity(recent_messages, entity)

def check_activity(messages, entity) -> (bool, str | None):
    if len(messages) == 0:
        return False, "канал пустой"
    with_text = [m for m in messages if m.message]
    if len(with_text) < MIN_POSTS_WITH_TEXT:       # напр. 3
        return False, "слишком мало текстовых постов"
    last_post_age_days = (now - max(m.date for m in with_text)).days
    if last_post_age_days > MAX_INACTIVE_DAYS:      # напр. 60
        return False, f"последний пост {last_post_age_days} дн. назад — канал заброшен"
    if getattr(entity, "participants_count", None) and entity.participants_count < MIN_SUBSCRIBERS:
        return False, "слишком мало подписчиков"    # опционально, Telethon отдаёт не всегда
    return True, None
```

### 3.2 AI-классификатор релевантности

Переиспользуем существующий LLM-клиент (`llm/client.py`,
паттерн как в `services/interest_categorizer.py`) — отдельный промпт
"это канал про конкурсы/гранты/стажировки/хакатоны для СНГ-студентов?".
На вход — не все посты, а компактная выборка (заголовки/первые ~5
последних постов), чтобы не жечь токены на каждый /add_channel.

```
async def classify_channel_relevance(sample_texts: list[str]) -> ChannelClassification:
    # ChannelClassification: is_relevant: bool, confidence: 0..1, reason: str, category: str|None
    prompt = build_channel_relevance_prompt(sample_texts)
    result = await llm.classify_channel(prompt)   # новый метод в llm/client.py,
                                                    # аналогичный classify_opportunity()
    return result
```

Причины отсева (не пропускать в общую базу): личный/приватный чат
(жалобы/чаты поддержки), реклама/криптоспам, нерелевантная тематика
(новости, мемы, курсы не по теме), дубли контента другого уже
существующего канала (плагиат-агрегатор — низкий приоритет, не MVP).

### 3.3 Итоговый quality_score

```
quality_score = round(100 * (
    0.6 * classification.confidence * (1 if classification.is_relevant else 0)
    + 0.4 * activity_score(messages)     # 0..1, напр. min(1, with_text_count / 10)
))

if quality_score >= 70:
    status = "verified"       # авто (после MVP, п.8)
elif quality_score >= 40:
    status = "pending"        # на ручной approve
else:
    status = "rejected"
```

На MVP-этапе (см. §8) авто-verified не включаем: **любой новый канал,
прошедший `validate_public_channel` + `check_activity` +
`is_relevant=True`, уходит в `pending` на ручной approve команды**,
только явный спам/нерелевантность отклоняется автоматически
(`is_relevant=False` или `activity_ok=False` → `rejected` сразу, без
нагрузки на модератора).

---

## 4. Приватность

Дефолт для UX: **добавление канала = вклад в общую базу Lumo**, это
должно быть сказано явно и подтверждено, а не быть скрытым default'ом.

Флоу (после успешной технической валидации канала, до записи в БД):

```
бот → inline-кнопки:
  "🌍 Добавить в общую базу Lumo (увидят все студенты)"
  "🔒 Только для меня (канал не попадёт в общий каталог)"

текст: "Канал @X будет использоваться для поиска конкурсов. Если это
открытый паблик — выбери первый вариант, это поможет другим студентам.
Если это закрытый чат школы/группы — выбери второй: посты будут
подбираться только тебе."
```

- `shared` (дефолт-рекомендация, не дефолт-без-подтверждения) →
  `MonitoredChannel.visibility = "shared"` — посты идут в общий
  `CatalogOpportunity`, видны всем подходящим пользователям.
- `private` → `MonitoredChannel.visibility = "private"` — канал
  мониторится, но извлечённые `CatalogOpportunity` помечаются
  недоступными для общего каталога (фильтр по `monitored_channel.visibility`
  в `OpportunityCatalogService`/`OpportunityCatalogRepository` при выдаче
  всем, кроме добавившего пользователя).

Технически: приватные каналы **не` join'ятся в общий рейтинг/поиск**
(`catalog_rerank.py`, `webapp_catalog.py`), только в персональный
`instant_match_for_user` для того, кто добавил.

Ограничение: один и тот же приватный канал, добавленный двумя разными
пользователями с разным выбором приватности — берём наиболее открытый
выбор (`shared` побеждает `private`), т.к. канал технически публичный по
Telegram-доступу; `private` — это ограничение видимости в Lumo, а не
секретность канала. В UI явно предупреждать: «если канал открытый и
кто-то другой уже добавил его в общую базу, твой выбор "только для
меня" не гарантирует эксклюзивность результатов».

---

## 5. Схема БД

### 5.1 Решение: расширить `monitored_channels`, а не заводить отдельную `channels`

В требовании из ТЗ фигурирует таблица `channels`, но в проекте её роль
уже играет `monitored_channels` (общий реестр источников + дедуп +
курсор мониторинга). Заводить параллельную `channels` означало бы вести
две сущности одного домена и синхронизировать их — вместо этого
расширяем существующую таблицу нужными полями. Это меньше миграций и
нет риска рассинхрона.

```sql
ALTER TABLE monitored_channels ADD COLUMN status VARCHAR(16) NOT NULL DEFAULT 'verified';
  -- 'pending' | 'verified' | 'rejected'
  -- существующие строки (seed + уже мониторящиеся) мигрируют как 'verified'
ALTER TABLE monitored_channels ADD COLUMN visibility VARCHAR(16) NOT NULL DEFAULT 'shared';
  -- 'shared' | 'private'
ALTER TABLE monitored_channels ADD COLUMN quality_score INTEGER NULL;
ALTER TABLE monitored_channels ADD COLUMN is_public BOOLEAN NOT NULL DEFAULT TRUE;
  -- дублирует признак из ChannelResolver.ChannelInfo.is_public, но сейчас нигде не сохраняется
ALTER TABLE monitored_channels ADD COLUMN added_by_user_id INTEGER NULL REFERENCES users(id) ON DELETE SET NULL;
  -- кто первый добавил (для геймификации и модерации); NULL для seed-каналов
ALTER TABLE monitored_channels ADD COLUMN rejected_reason TEXT NULL;
ALTER TABLE monitored_channels ADD COLUMN verified_at TIMESTAMPTZ NULL;
ALTER TABLE monitored_channels ADD COLUMN contributed_opportunities_count INTEGER NOT NULL DEFAULT 0;
  -- денормализованный счётчик для геймификации (инкремент при создании CatalogOpportunity
  -- с is_opportunity=True из raw_message этого канала — избегаем дорогого JOIN на каждый /my_channels)

CREATE INDEX ix_monitored_channels_status ON monitored_channels(status);
```

`UserChannel` (подписка пользователя) и `SeedChannel` (админский
seed-лист) не меняются — они уже покрывают «кто на что подписан» и
«какие каналы админ считает базовыми».

### 5.2 Rate-limit — без новой таблицы

Вместо отдельной таблицы счётчиков переиспользуем существующий
`EventRepository`/`Event` (`event_type="channel_submit"`, уже есть
похожее `channel_added`) — в кодовой базе так уже считается активность
(`services/analytics.py`, `admin_active_users.py`). Rate-limit —
`SELECT count(*) FROM events WHERE user_id=? AND event_type='channel_submit' AND created_at > now() - interval '1 day'`.
Плюс: не плодим схему, есть полный аудит-лог кто/когда подавал.

### 5.3 Геймификация — тоже без новой таблицы (MVP)

`contributed_opportunities_count` на `monitored_channels` +
`added_by_user_id` достаточно для «твой канал принёс N конкурсов».
Бонус (7 дней премиума) выдаётся через уже существующий
`services/subscription_grant.py::grant_trial(session, user, days=7)` —
разовая операция в момент `status → verified`, без отдельной таблицы
наград (событие логируется через `EventRepository` как
`channel_verified_bonus_granted`).

### 5.4 ER-фрагмент (изменённые/связанные сущности)

```
users ──< user_channels >── monitored_channels ──< raw_messages ──< catalog_opportunities
  │                              (status, visibility,                     │
  │                               quality_score,                          │
  └── added_by_user_id ──────────  is_public,                             │
                                    contributed_opportunities_count) ──────┘
                                          ▲
                                    seed_channels (админский список,
                                    всегда status='verified')
```

---

## 6. Пайплайн: добавление → верификация → парсинг → извлечение → общая база

```python
async def handle_new_channel_submission(user, raw_input: str) -> SubmissionResult:
    if await rate_limited(user):                      # §5.2
        return SubmissionResult.rate_limited()

    identifier = normalize_channel_identifier(raw_input)
    existing = await channel_repo.get_monitored_by_identifier(identifier)

    if existing and existing.status == "verified":
        await channel_repo.add_user_channel(user.id, identifier)   # существующий метод, без изменений
        return SubmissionResult.already_verified(existing)

    if existing and existing.status == "pending":
        await channel_repo.add_user_channel(user.id, identifier)   # подписываем сразу
        return SubmissionResult.pending(existing)

    if existing and existing.status == "rejected":
        return SubmissionResult.rejected(existing.rejected_reason)

    # новый канал
    info, error = await resolver.validate_public_channel(raw_input)  # существующий метод
    if error:
        return SubmissionResult.rejected(error)

    visibility = await ask_privacy_choice(user)         # §4, FSM-шаг

    recent = await client.get_messages(info_entity, limit=settings.monitor_initial_posts_limit)
    activity_ok, activity_reason = check_activity(recent, info_entity)   # §3.1
    if not activity_ok:
        await channel_repo.reject(identifier, reason=activity_reason)
        return SubmissionResult.rejected(activity_reason)

    classification = await classify_channel_relevance(
        [m.message for m in recent if m.message][:5]
    )                                                    # §3.2
    if not classification.is_relevant:
        await channel_repo.reject(identifier, reason=classification.reason)
        return SubmissionResult.rejected(classification.reason)

    quality_score = compute_quality_score(classification, recent)   # §3.3
    status = "pending"     # MVP: всегда pending, авто-verified — после MVP (§8)

    channel = await channel_repo.create_monitored(
        identifier, info.title,
        status=status, visibility=visibility,
        quality_score=quality_score, is_public=info.is_public,
        added_by_user_id=user.id,
    )
    await channel_repo.add_user_channel(user.id, identifier)

    # первичный backfill истории — переиспользуем существующий scan
    await MonitorWorker().scan_channel(channel.id)         # уже есть, сохраняет raw_messages
    # извлечение конкурсов из истории — тот же общий классификатор постов,
    # что и в фоновом цикле, просто вызванный сразу для этого канала:
    await OpportunityCatalogService().classify_pending(limit=settings.monitor_initial_posts_limit)

    if status == "pending":
        await notify_admin(f"🆕 Канал @{identifier} ждёт approve (score={quality_score})")
        return SubmissionResult.pending(channel)

    return SubmissionResult.verified(channel)


# Ручной approve админом (MVP):
async def approve_channel(monitored_channel_id: int) -> None:
    channel = await channel_repo.get(monitored_channel_id)
    channel.status = "verified"
    channel.verified_at = now()
    await session.commit()
    if channel.added_by_user_id:
        await grant_trial(session, channel.added_by_user_id, days=7)   # геймификация, §7
        await notify_user(channel.added_by_user_id, "🎉 Твой канал прошёл проверку! +7 дней премиума")


async def reject_channel(monitored_channel_id: int, reason: str) -> None:
    channel = await channel_repo.get(monitored_channel_id)
    channel.status = "rejected"
    channel.rejected_reason = reason
    await session.commit()
```

Важно: `classify_pending()` — это уже существующий общий метод
(`services/opportunity_catalog.py`), который проходит по всем
неклассифицированным `raw_messages` вне зависимости от канала. Вызов
его сразу после backfill — не новый механизм, а просто немедленный
(вместо ожидания следующего фонового цикла, `llm_processor_interval_seconds`)
триггер того же кода.

---

## 7. Геймификация

MVP-версия, без новой инфраструктуры:

- `/my_channels` — для каналов, где `added_by_user_id == user.id`,
  показываем: `@channel — status, +N конкурсов в базу`
  (`contributed_opportunities_count`).
- При переходе `pending → verified`: `grant_trial(user, days=7)` — уже
  существующая функция для триала, событие логируется
  `EventRepository.log("channel_verified_bonus_granted", ...)`.
- Инкремент `contributed_opportunities_count`: в
  `OpportunityCatalogRepository.create()` (там, где создаётся
  `CatalogOpportunity` с `is_opportunity=True`) — `+1` к счётчику канала
  через `raw_message.monitored_channel_id`.

Не MVP (опционально, отдельная итерация): приоритет в поиске/ранжирование
(`catalog_rerank.py`) для постов из каналов, добавленных активными
контрибьюторами — сложнее обосновать метрику, риск смещения качества
каталога ради геймификации.

---

## 8. Оценка объёма работ

MVP = без авто-верификации, с ручным approve команды. Оценка в
человеко-днях (1 разработчик, знакомый с кодовой базой).

| Блок | Дни | Комментарий |
|---|---|---|
| Миграция БД (`monitored_channels` + индекс + backfill `status='verified'` для существующих строк) | 0.5 | Alembic-скрипт, простая |
| Rate-limit (5/24ч через `Event`) + сообщение об ошибке | 0.5 | Переиспользует `EventRepository` |
| Расширение dedup-логики в `process_channel_input` (3 ветки: verified/pending/rejected) | 1 | Логика уже частично есть, добавить ветвление по `status` |
| FSM-шаг «приватность» (inline-кнопки, новое состояние, обработчик callback) | 1 | Новый UI-шаг + текст |
| Проверка активности (`check_activity`) на уже забираемых `recent messages` | 0.5 | Данные уже есть в first-scan, просто добавить проверку |
| AI-классификатор релевантности канала (промпт + `llm/client.py` метод + fallback) | 1.5 | Новый промпт, тестирование на реальных каналах (спам/не спам) |
| `quality_score` расчёт + пороги + сохранение | 0.5 | Простая формула |
| Admin-флоу: `/channel_queue`, approve/reject callbacks, уведомление админу | 1.5 | Новые хендлеры + клавиатура, по образцу существующих admin-хендлеров |
| Backfill истории + немедленный вызов `classify_pending` после approve/scan | 0.5 | Переиспользует `MonitorWorker.scan_channel` + `classify_pending` |
| Геймификация: `contributed_opportunities_count`, `/my_channels` UI, `grant_trial` при approve | 1 | Точечные правки в 2-3 местах |
| Privacy-фильтрация `visibility=private` в выдаче каталога (`OpportunityCatalogRepository`/`webapp_catalog.py`) | 1 | Нужно аккуратно не сломать текущую выдачу для всех пользователей |
| Ручное тестирование сценариев (дубликат/спам/приватный/пустой канал) + правки текстов | 1 | На реальных Telegram-каналах через staging Telethon-сессию |
| **Итого MVP** | **~9.5 дней** | Один разработчик, без автоматизации approve |

После MVP (не в оценке выше, отдельные итерации):
- авто-verified по порогу `quality_score` без участия админа (~1-2 дня
  после накопления статистики по ручным approve/reject, чтобы откалибровать
  пороги);
- приоритет в поиске для контрибьюторов (~2-3 дня, требует продуктового
  решения по метрике);
- защита от повторной отправки одного и того же `rejected` канала чаще
  раза в N дней (~0.5 дня).

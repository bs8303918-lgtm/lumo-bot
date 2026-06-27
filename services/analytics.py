import json
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from analytics.event_types import EVENT_LABELS
from config import get_settings
from db.repositories.users import EventRepository
from services.admin_notify import notify_admin

logger = logging.getLogger(__name__)


def _format_user(username: str | None, telegram_id: int | None) -> str:
    if username:
        return f"@{username}"
    if telegram_id:
        return f"id{telegram_id}"
    return "?"


async def track(
    session: AsyncSession,
    event_type: str,
    *,
    user_id: int | None = None,
    related_id: int | None = None,
    metadata: dict | None = None,
    username: str | None = None,
    telegram_id: int | None = None,
    live: bool = False,
) -> None:
    """Записать событие в БД и опционально отправить админу."""
    await EventRepository(session).log(
        event_type,
        user_id=user_id,
        related_id=related_id,
        metadata=metadata,
    )
    logger.info(
        "analytics %s user_id=%s meta=%s",
        event_type,
        user_id,
        metadata or {},
    )
    if not live:
        return
    settings = get_settings()
    if not settings.admin_analytics_live or not settings.telegram_admin_chat_id:
        return
    label = EVENT_LABELS.get(event_type, event_type)
    user_ref = _format_user(username, telegram_id)
    meta = ""
    if metadata:
        parts = []
        for key, value in metadata.items():
            if key == "text_preview":
                parts.append(f"{value[:80]}…" if len(str(value)) > 80 else str(value))
            else:
                parts.append(f"{key}={value}")
        if parts:
            meta = "\n" + " · ".join(parts)
    await notify_admin(f"📊 {user_ref} — {label}{meta}")


def _pct(part: int, whole: int) -> str:
    if not whole:
        return "—"
    return f"{round(part / whole * 100, 1)}%"


def format_funnel_report(data: dict, *, days: int) -> str:
    e = data["events"]
    u = data["users"]
    stuck = data["stuck"]
    recent = data["recent"]

    reg = u.get("user_registered", 0) or e.get("user_registered", 0)
    welcome = u.get("welcome_shown", 0)
    started = u.get("set_interest_started", 0)
    too_short = e.get("interest_too_short", 0)
    interest = u.get("interest_set", 0)
    empty_cat = u.get("onboarding_empty_catalog", 0)
    no_match = u.get("onboarding_no_match", 0)
    got_cards = u.get("onboarding_cards", 0)
    browse = u.get("browse_category_click", 0)
    cards = e.get("card_sent", 0)
    channels = u.get("channel_added", 0)

    lines = [
        f"📈 Воронка Lumo ({days} дн.)\n",
        "1️⃣ Вход",
        f"  Новые регистрации: {reg}",
        f"  Welcome показан: {welcome}",
        f"  Повторный /start: {u.get('returning_start', 0)}",
        "",
        "2️⃣ Интерес",
        f"  Начали /set_interest: {started}",
        f"  Короткий текст (<25): {too_short}",
        f"  Сохранили интерес: {interest}",
        f"  → конверсия рег → интерес: {_pct(interest, reg)}",
        "",
        "3️⃣ Результат",
        f"  Каталог пуст: {empty_cat}",
        f"  0 карточек (есть каталог): {no_match}",
        f"  Получили карточки: {got_cards}",
        f"  Открыли категорию: {browse}",
        f"  → конверсия интерес → карточки: {_pct(got_cards, interest)}",
        "",
        "4️⃣ Вовлечение",
        f"  Карточек отправлено (событий): {cards}",
        f"  Добавили канал: {channels}",
        f"  «Подробнее»: {e.get('button_details_click', 0)} · "
        f"«Заявка»: {e.get('button_apply_click', 0)}",
        "",
        "⚠️ Застряли (всё время)",
        f"  Без интереса: {stuck['no_interest']}",
        f"  С интересом, 0 карточек: {stuck['no_cards']}",
    ]

    if recent:
        lines.append("")
        lines.append("🕐 Последние шаги:")
        for row in recent:
            ts = row["at"]
            if isinstance(ts, datetime):
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                ts_str = ts.astimezone(timezone.utc).strftime("%d.%m %H:%M")
            else:
                ts_str = str(ts)
            label = EVENT_LABELS.get(row["type"], row["type"])
            user_ref = row["user"] or "?"
            meta = row.get("meta") or ""
            if meta:
                meta = f" ({meta})"
            lines.append(f"  {ts_str} {user_ref} — {label}{meta}")

    lines.append("")
    lines.append("Обновить: /funnel · Сводка: /stats")
    return "\n".join(lines)

"""Admin: top active users with prompts and Telegram contact links."""

from __future__ import annotations

from datetime import datetime, timezone

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def format_ago(dt: datetime | None, *, now: datetime | None = None) -> str:
    ref = _aware(dt)
    if ref is None:
        return "—"
    current = now or datetime.now(timezone.utc)
    delta = current - ref
    mins = int(delta.total_seconds() / 60)
    if mins < 1:
        return "только что"
    if mins < 60:
        return f"{mins} мин назад"
    hours = mins // 60
    if hours < 48:
        return f"{hours} ч назад"
    days = hours // 24
    if days < 60:
        return f"{days} дн назад"
    return ref.strftime("%d.%m.%Y")


def user_contact_html(username: str | None, telegram_id: int) -> str:
    if username:
        handle = username.lstrip("@")
        return f'<a href="https://t.me/{handle}">@{handle}</a>'
    return f'<code>{telegram_id}</code> <i>(нет @ — ищи по ID)</i>'


def contact_keyboard(rows: list[dict], *, max_buttons: int = 8) -> InlineKeyboardMarkup | None:
    buttons: list[list[InlineKeyboardButton]] = []
    for row in rows:
        username = (row.get("username") or "").strip().lstrip("@")
        if not username:
            continue
        label = f"💬 @{username[:28]}"
        buttons.append([InlineKeyboardButton(text=label, url=f"https://t.me/{username}")])
        if len(buttons) >= max_buttons:
            break
    if not buttons:
        return None
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def format_active_users_report(
    rows: list[dict],
    *,
    days: int,
    total_active: int,
) -> str:
    lines = [
        f"🏆 <b>Топ активных</b> за {days} дн.",
        f"С промптами (AI-поиск): <b>{total_active}</b>",
        "",
    ]
    if not rows:
        lines.append("Пока никто не делал AI-запросов за этот период.")
        return "\n".join(lines)

    for i, row in enumerate(rows, start=1):
        contact = user_contact_html(row.get("username"), row["telegramId"])
        started = format_ago(row.get("createdAt"))
        last = format_ago(row.get("lastActiveAt"))
        interest = (row.get("interestPreview") or "").strip()
        interest_line = f"\n   🎯 {interest}…" if interest else ""
        plan = row.get("tariffPlan") or "freemium"
        lines.append(
            f"{i}. {contact}\n"
            f"   🤖 промптов: <b>{row['prompts']}</b> · событий: {row['eventsTotal']}\n"
            f"   📅 старт: {started} · был: {last}\n"
            f"   📡 каналов: {row['channelCount']} · карточек: {row['cardsTotal']} · {plan}"
            f"{interest_line}"
        )
    lines.extend(
        [
            "",
            "Написать: кнопки ниже (если есть @) или /user @username",
            "Детали: /user &lt;telegram_id&gt;",
        ]
    )
    return "\n".join(lines)


def format_user_activity_report(data: dict) -> str:
    contact = user_contact_html(data.get("username"), data["telegramId"])
    stats = data.get("stats") or {}
    today = stats.get("today", {})
    week = stats.get("7d", {})
    month = stats.get("30d", {})
    all_time = stats.get("all", {})

    interest = (data.get("interestQuery") or "").strip()
    interest_block = f"\n🎯 <b>Интерес:</b>\n{interest[:500]}" if interest else "\n🎯 Интерес не задан"

    return (
        f"👤 <b>Пользователь</b> {contact}\n"
        f"🆔 Telegram ID: <code>{data['telegramId']}</code>\n"
        f"📅 Регистрация: {format_ago(data.get('createdAt'))}\n"
        f"🕐 Последняя активность: {format_ago(data.get('lastActiveAt'))}\n"
        f"📡 Каналов: {data['channelCount']} · карточек всего: {data['cardsTotal']}\n"
        f"💳 Тариф: {data.get('tariffPlan') or 'freemium'}"
        f"{interest_block}\n\n"
        f"<b>Промпты (AI-поиск):</b>\n"
        f"  сегодня: {today.get('prompts', 0)}\n"
        f"  7 дн: {week.get('prompts', 0)}\n"
        f"  30 дн: {month.get('prompts', 0)}\n"
        f"  всего: {all_time.get('prompts', 0)}\n\n"
        f"<b>Все события:</b> сегодня {today.get('events', 0)} · "
        f"7д {week.get('events', 0)} · 30д {month.get('events', 0)} · "
        f"всего {all_time.get('events', 0)}"
    )


def parse_active_command_args(text: str) -> tuple[int, int]:
    """Returns (days, limit)."""
    parts = (text or "").split()
    days = 7
    limit = 15
    if len(parts) >= 2:
        try:
            days = max(1, min(365, int(parts[1])))
        except ValueError:
            pass
    if len(parts) >= 3:
        try:
            limit = max(5, min(30, int(parts[2])))
        except ValueError:
            pass
    return days, limit


def parse_user_lookup(text: str) -> str | None:
    parts = (text or "").split(maxsplit=1)
    if len(parts) < 2:
        return None
    return parts[1].strip().lstrip("@")

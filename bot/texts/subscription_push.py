"""Push-тексты подписки (Startify trial → upsell)."""

from __future__ import annotations

from datetime import datetime

from config import get_settings
from services.subscription import PLAN_CATALOG, RETAIL_PLAN_ORDER


def _format_expires(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    if dt.tzinfo is not None:
        from datetime import timezone

        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%d.%m.%Y")


def _price_lines() -> str:
    lines = []
    for plan_id in RETAIL_PLAN_ORDER:
        meta = PLAN_CATALOG.get(plan_id) or {}
        label = meta.get("label", plan_id)
        price = meta.get("priceKzt", 0)
        benefit = meta.get("benefit")
        extra = f" · {benefit}" if benefit else ""
        lines.append(f"• {label} — {price:,} ₸{extra}".replace(",", " "))
    return "\n".join(lines)


def _checkout_hint() -> str:
    settings = get_settings()
    checkout = settings.startify_checkout_url.strip()
    phone = settings.kaspi_payment_phone.strip() or "+7 775 499 8313"
    if checkout:
        return f"Оплата через Kaspi на сайте AI Startify или по номеру {phone}."
    return f"Оплата через Kaspi: {phone}."


def get_startify_trial_welcome(expires_at: datetime | None) -> str:
    return (
        "🎉 <b>Добро пожаловать в Lumo от AI Startify!</b>\n\n"
        "Вам подключён <b>пробный доступ на 7 дней</b>:\n"
        "• без лимита AI-поиска\n"
        "• ежедневные подборки грантов и стажировок\n"
        "• до 5 каналов в мониторинге\n\n"
        f"⏳ Активен до: <b>{_format_expires(expires_at)}</b>\n\n"
        "Следующий шаг — задай профиль:\n"
        "👉 /set_interest"
    )


def get_trial_remind_3d(expires_at: datetime | None) -> str:
    return (
        "🔥 <b>Осталось 3 дня пробного Lumo</b>\n\n"
        "Ты уже видишь подборки без лимита AI — не потеряй ритм, как в Duolingo streak 😉\n\n"
        "После trial снова будет 3 AI-запроса в день.\n\n"
        "<b>Безлимит навсегда</b> — 49 000 ₸ (разовая оплата).\n"
        "Или подписка от 990 ₸/мес:\n"
        f"{_price_lines()}\n\n"
        f"{_checkout_hint()}\n\n"
        "👇 Выбери тариф — кнопка ниже"
    )


def get_trial_remind_1d(expires_at: datetime | None) -> str:
    return (
        "⏰ <b>Завтра заканчивается пробный Lumo</b>\n\n"
        f"Доступ до: <b>{_format_expires(expires_at)}</b>\n\n"
        "Сегодня последний день ловить возможности <b>без лимита</b>.\n"
        "Завтра AI-поиск снова станет 3 раза в день.\n\n"
        "💎 <b>Хит:</b> 6 месяцев — 7 990 ₸ (экономия 1 990 ₸)\n"
        "🏆 <b>Навсегда:</b> Безлимит — 49 000 ₸ один раз\n\n"
        f"{_checkout_hint()}"
    )


def get_trial_expired_message() -> str:
    return (
        "🔒 <b>Пробный период Lumo завершён</b>\n\n"
        "Спасибо, что попробовал Lumo × AI Startify!\n\n"
        "Сейчас снова действует бесплатный режим:\n"
        "• 3 AI-запроса в день\n"
        "• каталог и уведомления остаются\n\n"
        "Хочешь снова <b>без лимита</b> и ежедневные подборки на полную?\n\n"
        f"{_price_lines()}\n\n"
        "📱 Для счёта в Kaspi понадобится номер телефона, привязанный к Kaspi.\n"
        f"{_checkout_hint()}"
    )


def get_trial_winback_3d() -> str:
    return (
        "👋 <b>Мы скучаем — без лимита AI всего в одном шаге</b>\n\n"
        "3 дня назад закончился trial. За это время в каталоге могли появиться "
        "новые гранты и стажировки под твой профиль.\n\n"
        "🚀 Вернись на полную мощность:\n"
        "• <b>3 месяца</b> — 4 990 ₸\n"
        "• <b>6 месяцев</b> — 7 990 ₸\n"
        "• <b>12 месяцев</b> — 11 880 ₸\n"
        "• <b>Безлимит навсегда</b> — 49 000 ₸\n\n"
        f"{_checkout_hint()}"
    )


def get_trial_winback_7d() -> str:
    return (
        "🎯 <b>Последнее напоминание от Lumo</b>\n\n"
        "Неделю назад у тебя был полный доступ — AI без лимита и умные подборки.\n\n"
        "Один клик — и снова не пропустишь дедлайны по грантам и хакатонам.\n\n"
        "🔥 Спец-предложение: <b>6 месяцев — 7 990 ₸</b>\n"
        "или <b>Безлимит — 49 000 ₸</b> (платишь один раз).\n\n"
        f"{_checkout_hint()}\n\n"
        "Если не актуально — просто игнорируй. Мы всё равно пришлём важное из твоих каналов."
    )

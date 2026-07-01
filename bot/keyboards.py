from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

from config import get_settings
from services.url_utils import is_valid_telegram_button_url, normalize_https_url
from services.interest_matcher import is_domain_category, is_standard_category, tag_display

BTN_TRACK_CHANNEL = "🔍 Отслеживать канал"
BTN_MY_CRITERIA = "👤 Мои критерии"
BTN_COMMUNITY = "👥 Сообщество"
BTN_HELP = "📖 Помощь"


def webapp_open_inline() -> InlineKeyboardMarkup | None:
    """Fresh Mini App URL — use this if the blue Open button shows an old tunnel."""
    url = get_settings().telegram_webapp_base_url
    if not url:
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📱 Open Mini App",
                    web_app=WebAppInfo(url=url),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔗 Открыть ссылку",
                    url=url,
                )
            ],
        ]
    )


def subscription_upsell_keyboard() -> InlineKeyboardMarkup | None:
    """Кнопка оплаты Startify + Mini App."""
    settings = get_settings()
    rows: list[list[InlineKeyboardButton]] = []
    checkout = normalize_https_url(settings.startify_checkout_url.strip())
    if checkout and is_valid_telegram_button_url(checkout):
        rows.append([InlineKeyboardButton(text="💳 Выбрать тариф и оплатить", url=checkout)])
    webapp = settings.telegram_webapp_base_url
    if webapp:
        rows.append(
            [
                InlineKeyboardButton(
                    text="📱 Тарифы в Mini App",
                    web_app=WebAppInfo(url=webapp),
                )
            ]
        )
    if not rows:
        return None
    return InlineKeyboardMarkup(inline_keyboard=rows)


def community_join_inline() -> InlineKeyboardMarkup | None:
    url = normalize_https_url(get_settings().community_telegram_url)
    if not url or not is_valid_telegram_button_url(url):
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👥 Вступить в сообщество", url=url)],
        ]
    )


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_TRACK_CHANNEL), KeyboardButton(text=BTN_MY_CRITERIA)],
            [KeyboardButton(text=BTN_COMMUNITY), KeyboardButton(text=BTN_HELP)],
        ],
        resize_keyboard=True,
    )


def channel_list_keyboard(channels: list) -> InlineKeyboardMarkup:
    buttons = []
    for ch in channels:
        title = ch.channel_title or f"@{ch.channel_identifier}"
        buttons.append([
            InlineKeyboardButton(
                text=f"🗑 {title}",
                callback_data=f"remove_channel:{ch.id}",
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def interest_browse_keyboard(categories: list[str], category_counts: dict[str, int]) -> InlineKeyboardMarkup | None:
    """Кнопки категорий из профиля пользователя (типы + сферы)."""
    buttons: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    seen: set[str] = set()
    for category in categories:
        key = category.lower().strip()
        if not key or key in seen or key == "другое":
            continue
        seen.add(key)
        emoji, label = tag_display(key)
        count = category_counts.get(key, 0)
        suffix = f" ({count})" if count else ""
        row.append(
            InlineKeyboardButton(
                text=f"{emoji} {label}{suffix}",
                callback_data=f"browse:{key}",
            )
        )
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    if not buttons:
        return catalog_browse_keyboard(category_counts)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def catalog_browse_keyboard(category_counts: dict[str, int]) -> InlineKeyboardMarkup | None:
    from services.interest_matcher import CATEGORY_DISPLAY, OPPORTUNITY_TYPES

    buttons: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for opp_type in OPPORTUNITY_TYPES:
        if opp_type == "другое":
            continue
        count = category_counts.get(opp_type, 0)
        if count <= 0:
            continue
        emoji, label = CATEGORY_DISPLAY[opp_type]
        row.append(
            InlineKeyboardButton(
                text=f"{emoji} {label} ({count})",
                callback_data=f"browse:{opp_type}",
            )
        )
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    if not buttons:
        return None
    return InlineKeyboardMarkup(inline_keyboard=buttons)

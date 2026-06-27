"""Имена событий аналитики — единый список для логов и воронки."""

# Воронка онбординга
USER_REGISTERED = "user_registered"
WELCOME_SHOWN = "welcome_shown"
RETURNING_START = "returning_start"
SET_INTEREST_STARTED = "set_interest_started"
INTEREST_TOO_SHORT = "interest_too_short"
INTEREST_SET = "interest_set"
ONBOARDING_EMPTY_CATALOG = "onboarding_empty_catalog"
ONBOARDING_NO_MATCH = "onboarding_no_match"
ONBOARDING_CARDS = "onboarding_cards"
BROWSE_CATEGORY_CLICK = "browse_category_click"

# Вовлечение
CARD_SENT = "card_sent"
DAILY_DIGEST_MATCH = "daily_digest_match"
DAILY_DIGEST_EMPTY = "daily_digest_empty"
AI_SEARCH = "ai_search"
BUTTON_DETAILS_CLICK = "button_details_click"
BUTTON_APPLY_CLICK = "button_apply_click"

# Mini App — каталог
CATALOG_VIEW = "catalog_view"
CATALOG_APPLY_CLICK = "catalog_apply_click"
CATALOG_TELEGRAM_CLICK = "catalog_telegram_click"

CHANNEL_ADDED = "channel_added"
CHANNEL_REMOVED = "channel_removed"

# Промо-кампании
CAMPAIGN_SENT = "campaign_sent"
CAMPAIGN_TELEGRAM_CLICK = "campaign_telegram_click"
CAMPAIGN_LINK_CLICK = "campaign_link_click"
CAMPAIGN_APPLY_CLICK = "campaign_apply_click"

MAINTENANCE_NOTICE_SENT = "maintenance_notice_sent"
COMMUNITY_INVITE_SENT = "community_invite_sent"

# Ошибки
LLM_ERROR = "llm_error"
HANDLER_ERROR = "handler_error"

FUNNEL_EVENT_TYPES = (
    USER_REGISTERED,
    WELCOME_SHOWN,
    RETURNING_START,
    SET_INTEREST_STARTED,
    INTEREST_TOO_SHORT,
    INTEREST_SET,
    ONBOARDING_EMPTY_CATALOG,
    ONBOARDING_NO_MATCH,
    ONBOARDING_CARDS,
    BROWSE_CATEGORY_CLICK,
    CARD_SENT,
    DAILY_DIGEST_MATCH,
    DAILY_DIGEST_EMPTY,
    CHANNEL_ADDED,
)

EVENT_LABELS: dict[str, str] = {
    USER_REGISTERED: "регистрация",
    WELCOME_SHOWN: "welcome",
    RETURNING_START: "повторный /start",
    SET_INTEREST_STARTED: "начал /set_interest",
    INTEREST_TOO_SHORT: "короткий текст",
    INTEREST_SET: "сохранил интерес",
    ONBOARDING_EMPTY_CATALOG: "каталог пуст",
    ONBOARDING_NO_MATCH: "0 карточек",
    ONBOARDING_CARDS: "получил карточки",
    BROWSE_CATEGORY_CLICK: "каталог по категории",
    CARD_SENT: "карточка отправлена",
    DAILY_DIGEST_MATCH: "ежедневная подборка",
    DAILY_DIGEST_EMPTY: "ежедневно: пусто + рекомендации",
    AI_SEARCH: "AI-поиск",
    BUTTON_DETAILS_CLICK: "«Подробнее» (бот)",
    BUTTON_APPLY_CLICK: "«Подать заявку» (бот)",
    CATALOG_VIEW: "просмотр в Mini App",
    CATALOG_APPLY_CLICK: "клик «Заявка» (Mini App)",
    CATALOG_TELEGRAM_CLICK: "клик Telegram (Mini App)",
    CHANNEL_ADDED: "добавил канал",
    CHANNEL_REMOVED: "удалил канал",
    CAMPAIGN_SENT: "кампания: отправлено",
    CAMPAIGN_TELEGRAM_CLICK: "кампания: Telegram",
    CAMPAIGN_LINK_CLICK: "кампания: ссылка",
    CAMPAIGN_APPLY_CLICK: "кампания: форма заявки",
    MAINTENANCE_NOTICE_SENT: "техобслуживание: извинение",
    LLM_ERROR: "ошибка LLM",
    HANDLER_ERROR: "ошибка бота",
}

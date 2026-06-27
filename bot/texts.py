from config import get_settings
from db.repositories.users import normalize_channel_identifier
from services.interest_matcher import is_domain_category, tag_display


def get_community_invite_text() -> str:
    handle = get_settings().community_telegram_handle.strip() or "Lumo Community"
    return (
        f"👥 <b>{handle}</b>\n\n"
        "Чат для тех, кто пользуется Lumo: делимся возможностями, "
        "хакатонами и стартап-программами, задаём вопросы и находим команды.\n\n"
        "Нажми кнопку ниже, чтобы вступить 👇"
    )


def get_welcome_text() -> str:
    return (
        "👋 Привет! Я Lumo, твой ИИ-помощник по поиску возможностей.\n\n"
        "Я мониторю каналы и присылаю тебе только те хакатоны, стажировки и гранты, "
        "которые подходят лично под твой бэкграунд.\n\n"
        "🎉 Чтобы начать, активируй меня одной командой:\n\n"
        "👉 /set_interest — просто напиши про себя, остальное я сделаю 🎯"
    )


# Эффект при появлении сообщения (🎉 confetti) — только в личке с ботом
WELCOME_MESSAGE_EFFECT_ID = "5046509860389126442"


def get_help_text() -> str:
    contact = get_settings().support_contact
    return (
        "📖 <b>Команды Lumo</b>\n\n"
        "/set_interest — профиль и что ищешь\n"
        "/add_channel — добавить канал (до 5)\n"
        "/my_channels — твои каналы\n"
        "/app — каталог и AI (синяя кнопка Open слева)\n"
        "/ping — бот онлайн?\n"
        "/status — когда последний скан\n"
        f"/bug — баг или идея ({contact})\n"
        "👥 Сообщество — кнопка в меню или /community\n\n"
        "💡 Сначала /set_interest — без профиля карточки не приходят."
    )


SET_INTEREST_PROMPT = (
    "🎯 Напиши одним сообщением — как в чате с ассистентом:\n"
    "• кто ты\n"
    "• что ищешь — конкурсы, гранты, стипендии, хакатоны…\n\n"
    "<i>Пример: Студент IT, ищу хакатоны и стажировки в AI.</i>\n\n"
    "Сразу подберу подходящее из базы ⚡"
)

SET_INTEREST_TOO_SHORT = (
    "✍️ Маловато — добавь пару строк: кто ты и какие возможности ищешь."
)

HELP_TEXT = get_help_text()


def bug_report_hint() -> str:
    return f"Баг? /bug или {get_settings().support_contact}"


def get_seed_channels_list() -> str:
    settings = get_settings()
    if not settings.seed_channels_file.exists():
        return "• @startup_course_com\n• @uppertunity"
    lines = [
        line.strip()
        for line in settings.seed_channels_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return "\n".join(f"• @{normalize_channel_identifier(line)}" for line in lines) or "• @startup_course_com"


def get_searching_instant() -> str:
    return "🔍 Ищу подходящие возможности в базе..."


def get_searching_message(catalog_count: int, posts_count: int, channels_count: int) -> str:
    if catalog_count > 0:
        return (
            f"🔍 Ищу подходящие возможности...\n"
            f"Подбираю из базы: {catalog_count} актуальных записей по категориям."
        )
    if posts_count <= 0:
        return (
            "🔍 Ищу подходящие возможности...\n"
            "Подключаюсь к каналам — это займёт несколько секунд."
        )
    return (
        f"🔍 Ищу подходящие возможности...\n"
        f"Классифицирую {posts_count} постов из {channels_count} каналов."
    )


def get_search_progress(checked: int, total: int, *, from_catalog: bool = False) -> str:
    if from_catalog:
        return f"🔍 Подбираю из базы... проверено {checked} из {total}"
    return f"🔍 Ищу... просмотрено {checked} из {total} постов"


def get_add_channel_hint() -> str:
    return (
        "\n\n📡 Можешь добавить свои каналы — я буду читать их за тебя: /add_channel "
        "(до 5 штук, только публичные)."
    )


def format_categories_preview(category_counts: dict[str, int] | None, *, profile_categories: list[str] | None = None) -> str:
    if profile_categories:
        lines: list[str] = []
        for category in profile_categories:
            emoji, label = tag_display(category)
            count = (category_counts or {}).get(category, 0)
            suffix = f" — {count}" if count else ""
            lines.append(f"• {emoji} {label}{suffix}")
        if lines:
            return (
                "\n\n📂 Твои категории:\n"
                + "\n".join(lines)
                + "\n\n👇 Нажми категорию — покажу свежие примеры"
            )
    if not category_counts:
        return ""
    lines = []
    from services.interest_matcher import CATEGORY_DISPLAY, OPPORTUNITY_TYPES

    for category in OPPORTUNITY_TYPES:
        if category == "другое":
            continue
        count = category_counts.get(category, 0)
        if count <= 0:
            continue
        emoji, label = CATEGORY_DISPLAY[category]
        lines.append(f"• {emoji} {label} — {count}")
    if not lines:
        return ""
    return (
        "\n\n📂 Сейчас в базе есть:\n"
        + "\n".join(lines)
        + "\n\n👇 Нажми категорию — покажу свежие примеры"
    )


def format_browse_category_message(category: str, items: list) -> str:
    emoji, label = tag_display(category)
    if not items:
        return f"{emoji} В категории «{label}» пока нет активных записей."
    lines = [f"✨ Lumo · примеры: {emoji} {label}\n"]
    for idx, item in enumerate(items, start=1):
        title = item.title or "Возможность"
        deadline = item.deadline or "не указан"
        lines.append(f"{idx}. «{title}»")
        lines.append(f"   📅 {deadline}")
        lines.append(f"   👉 {item.message_link}")
        if idx < len(items):
            lines.append("")
    lines.append("\nЭто превью из базы — персональные подборки пришлю сам.")
    return "\n".join(lines)


def get_onboarding_after_interest(
    sent_cards: int,
    *,
    category_counts: dict[str, int] | None = None,
    profile_categories: list[str] | None = None,
) -> str:
    if sent_cards == 1:
        count_line = "🎉 Нашёл 1 подходящую возможность — смотри подборку выше."
    elif sent_cards > 1:
        count_line = f"🎉 Нашёл {sent_cards} подходящих — смотри подборку выше."
    else:
        return get_no_matches_onboarding(
            category_counts=category_counts,
            profile_categories=profile_categories,
        )
    return (
        f"{count_line}\n"
        "Дальше буду присылать подборками по 5 штук — без спама."
        f"{get_add_channel_hint()}\n\n"
        "ℹ️ /help"
    )


def format_daily_recommendations(items: list) -> str:
    if not items:
        return ""
    lines = ["Но могу порекомендовать посмотреть:\n"]
    for idx, item in enumerate(items, start=1):
        title = item.title or "Возможность"
        deadline = item.deadline or "не указан"
        link = item.message_link or ""
        lines.append(f"{idx}. «{title}»")
        lines.append(f"   📅 {deadline}")
        if link:
            lines.append(f"   👉 {link}")
        if idx < len(items):
            lines.append("")
    lines.append("\nЭто похожие варианты из базы — не персональный матч, но может зайти.")
    return "\n".join(lines)


def get_daily_empty_digest_message(
    recommendations: list,
    *,
    category_counts: dict[str, int] | None = None,
) -> str:
    rec_block = format_daily_recommendations(recommendations)
    categories_block = format_categories_preview(category_counts or {}) if not rec_block else ""
    body = rec_block or (
        "Пока в базе мало свежего под твой профиль."
        f"{categories_block}"
    )
    return (
        "😔 Сегодня нового под твоой профиль не нашёл.\n\n"
        f"{body}\n\n"
        "⏰ Каналы перепроверяются каждые 24 часа — как только появится что-то "
        "релевантное, пришлю подборкой."
        f"{get_add_channel_hint()}\n\n"
        "ℹ️ /help"
    )


def get_no_matches_onboarding(
    *,
    category_counts: dict[str, int] | None = None,
    profile_categories: list[str] | None = None,
) -> str:
    channels = get_seed_channels_list()
    categories_block = format_categories_preview(
        category_counts or {},
        profile_categories=profile_categories,
    )
    return (
        "😔 Пока не нашёл подходящих возможностей по твоему запросу.\n\n"
        "⏰ Каналы перепроверяются каждые 24 часа — как только появится что-то "
        "релевантное, пришлю подборкой."
        f"{categories_block}\n\n"
        "📡 Я уже читаю эти каналы и отбираю лучшее под твой профиль:\n"
        f"{channels}\n\n"
        "Можешь подписаться — там много полезного, а я буду присылать только "
        "то, что подходит именно тебе."
        f"{get_add_channel_hint()}\n\n"
        "ℹ️ /help"
    )


def get_no_posts_yet_onboarding() -> str:
    channels = get_seed_channels_list()
    return (
        "📭 Пока нет сохранённых постов из каналов — первый скан займёт до 24 часов.\n\n"
        "⏰ Как только появятся новые объявления, сразу проверю и пришлю подборку.\n\n"
        "📡 Я уже подключён к этим каналам:\n"
        f"{channels}\n\n"
        "Можешь подписаться — там много полезного, а я буду присылать только "
        "то, что подходит именно тебе."
        f"{get_add_channel_hint()}\n\n"
        "ℹ️ /help"
    )


def get_interest_updated_message(
    sent_cards: int,
    *,
    category_counts: dict[str, int] | None = None,
    profile_categories: list[str] | None = None,
) -> str:
    if sent_cards > 0:
        return (
            f"✅ Профиль обновлён — нашёл {sent_cards} подходящих по новым критериям.\n\n"
            "Дальше буду присылать новые сам."
            f"{get_add_channel_hint()}\n\n"
            "ℹ️ /help"
        )
    categories_block = format_categories_preview(
        category_counts or {},
        profile_categories=profile_categories,
    )
    if categories_block:
        body = (
            "✅ Профиль обновлён.\n\n"
            "🔍 По новым критериям пока ничего точного — продолжу искать "
            f"и пришлю, когда найду.{categories_block}"
        )
    else:
        body = (
            "✅ Профиль обновлён.\n\n"
            "🔍 По новым критериям пока ничего не подошло — продолжу искать "
            "и пришлю, когда найду."
        )
    return f"{body}{get_add_channel_hint()}\n\nℹ️ /help"

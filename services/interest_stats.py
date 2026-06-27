"""Admin analytics: what users are looking for."""

from __future__ import annotations

from dataclasses import dataclass

from db.models import User
from db.repositories.opportunity_catalog import parse_interest_categories
from services.interest_matcher import CATEGORY_DISPLAY, extract_categories_from_text

_BROAD_DEFAULT = frozenset(
    {"конкурс", "грант", "стипендия", "хакатон", "стажировка", "мероприятие"}
)

TOPIC_PRESETS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("🚀", "Стартапы", ("стартап", "startup", "start-up", "start up")),
    ("🤖", "AI / ML", (" ai", "ai ", "ml", "machine learning", "нейросет", "искусственн", "data science")),
    ("💰", "Гранты", ("грант", "grant")),
    ("🎓", "Стипендии", ("стипенди", "scholarship")),
    ("💻", "Хакатоны", ("хакатон", "hackathon", "datathon")),
    ("🏢", "Стажировки", ("стажиров", "internship", "intern ", "trainee")),
    ("🏆", "Конкурсы / питчи", ("конкурс", "contest", "pitch", "питч", "challenge")),
    ("💵", "Денежные призы", ("денежн", "cash prize", "prize money", "призовой фонд", "выиграть")),
    ("📅", "Мероприятия", ("митап", "meetup", "конферен", "воркшоп", "workshop", "форум")),
    ("🇰🇿", "Казахстан", ("казахстан", "астана", "алматы", "astana", "almaty")),
    ("🌍", "Зарубеж", ("erasmus", "fulbright", "chevening", "daad", "за рубеж", "abroad")),
)


@dataclass(frozen=True)
class InterestOverview:
    total_users: int
    with_interest: int
    category_counts: dict[str, int]
    broad_interest_count: int
    topic_counts: list[tuple[str, str, int]]
    sample_queries: list[str]


@dataclass(frozen=True)
class TopicMatch:
    topic: str
    matched_keywords: tuple[str, ...]
    users: list[User]
    with_interest_total: int
    total_users: int


def _user_categories(user: User) -> list[str]:
    saved = parse_interest_categories(user.interest_categories_json)
    if saved:
        return saved
    return extract_categories_from_text(user.interest_query or "")


def is_broad_interest(user: User) -> bool:
    if parse_interest_categories(user.interest_categories_json):
        return False
    return not extract_categories_from_text(user.interest_query or "")


def _normalize_topic(topic: str) -> str:
    return topic.strip().lower().lstrip("#")


def _topic_keywords(topic: str) -> tuple[str, ...]:
    normalized = _normalize_topic(topic)
    if not normalized:
        return ()
    for _emoji, _label, keywords in TOPIC_PRESETS:
        if normalized in keywords or normalized == _label.lower():
            return keywords
    return (normalized,)


def interest_query_matches_topic(text: str, topic: str) -> bool:
    if not text or not topic:
        return False
    lowered = text.lower()
    for keyword in _topic_keywords(topic):
        if keyword.strip() and keyword in lowered:
            return True
    return False


def matched_topic_keywords(text: str, topic: str) -> tuple[str, ...]:
    lowered = (text or "").lower()
    return tuple(kw for kw in _topic_keywords(topic) if kw.strip() and kw in lowered)


def build_interest_overview(
    users: list[User],
    *,
    total_users: int,
    topic_limit: int = 10,
    sample_limit: int = 5,
) -> InterestOverview:
    with_interest = [u for u in users if u.interest_query and u.interest_query.strip()]
    category_counts: dict[str, int] = {}
    broad_count = 0

    for user in with_interest:
        if is_broad_interest(user):
            broad_count += 1
            continue
        for category in _user_categories(user):
            category_counts[category] = category_counts.get(category, 0) + 1

    topic_counts: list[tuple[str, str, int]] = []
    for emoji, label, keywords in TOPIC_PRESETS:
        count = sum(
            1
            for user in with_interest
            if any(kw in (user.interest_query or "").lower() for kw in keywords)
        )
        if count:
            topic_counts.append((emoji, label, count))
    topic_counts.sort(key=lambda row: row[2], reverse=True)
    topic_counts = topic_counts[:topic_limit]

    samples = [
        (user.interest_query or "").strip().replace("\n", " ")
        for user in sorted(with_interest, key=lambda u: u.updated_at or u.created_at, reverse=True)
    ]
    unique_samples: list[str] = []
    seen: set[str] = set()
    for query in samples:
        key = query.lower()
        if key in seen or not query:
            continue
        seen.add(key)
        unique_samples.append(query if len(query) <= 90 else query[:87] + "…")
        if len(unique_samples) >= sample_limit:
            break

    return InterestOverview(
        total_users=total_users,
        with_interest=len(with_interest),
        category_counts=category_counts,
        broad_interest_count=broad_count,
        topic_counts=topic_counts,
        sample_queries=unique_samples,
    )


def search_users_by_topic(
    users: list[User],
    topic: str,
    *,
    total_users: int | None = None,
) -> TopicMatch:
    with_interest = [u for u in users if u.interest_query and u.interest_query.strip()]
    matched = [u for u in with_interest if interest_query_matches_topic(u.interest_query or "", topic)]
    keywords = _topic_keywords(topic)
    matched_kw = matched_topic_keywords(
        " ".join(u.interest_query or "" for u in matched),
        topic,
    )
    if not matched_kw and keywords:
        matched_kw = keywords[:3]
    return TopicMatch(
        topic=_normalize_topic(topic),
        matched_keywords=matched_kw,
        users=matched,
        with_interest_total=len(with_interest),
        total_users=total_users if total_users is not None else len(users),
    )


def _pct(part: int, whole: int) -> str:
    if not whole:
        return "—"
    return f"{round(part / whole * 100, 1)}%"


def format_interest_overview(data: InterestOverview) -> str:
    lines = [
        "🎯 Интересы пользователей\n",
        f"Всего пользователей: {data.total_users}",
        f"С профилем интересов: {data.with_interest} ({_pct(data.with_interest, data.total_users)})",
        f"Без профиля: {data.total_users - data.with_interest}",
    ]

    if not data.with_interest:
        lines.append("\nПока никто не задал /set_interest.")
        lines.append("\nПоиск по теме: /interests стартап")
        return "\n".join(lines)

    if data.category_counts:
        lines.append("\n📂 По категориям:")
        ordered = sorted(data.category_counts.items(), key=lambda item: item[1], reverse=True)
        for category, count in ordered:
            emoji, label = CATEGORY_DISPLAY.get(category, ("•", category.capitalize()))
            lines.append(f"  {emoji} {label}: {count} ({_pct(count, data.with_interest)})")
    if data.broad_interest_count:
        lines.append(
            f"  🌐 Общий запрос (без конкретной категории): "
            f"{data.broad_interest_count} ({_pct(data.broad_interest_count, data.with_interest)})"
        )

    if data.topic_counts:
        lines.append("\n🔎 Популярные темы в тексте:")
        for emoji, label, count in data.topic_counts:
            lines.append(f"  {emoji} {label}: {count} чел.")

    if data.sample_queries:
        lines.append("\n💬 Примеры запросов:")
        for query in data.sample_queries:
            lines.append(f"  • «{query}»")

    lines.append("\nПоиск по теме: /interests стартап")
    lines.append("Другие темы: ai, грант, стипендия, хакатон, erasmus")
    return "\n".join(lines)


def _format_user_ref(user: User) -> str:
    if user.username:
        return f"@{user.username}"
    return f"id{user.telegram_id}"


def format_topic_match(data: TopicMatch, *, preview_limit: int = 8) -> str:
    count = len(data.users)
    if not data.topic:
        return "Укажи тему: /interests стартап"

    if not count:
        return (
            f"🔍 «{data.topic}» — 0 из {data.with_interest_total} "
            f"пользователей с профилем.\n\n"
            "Попробуй: стартап, ai, грант, стипендия, хакатон"
        )

    preset_label = next(
        (label for _emoji, label, keywords in TOPIC_PRESETS if data.topic in keywords or data.topic == label.lower()),
        data.topic,
    )
    kw_line = ""
    if data.matched_keywords:
        shown = ", ".join(sorted(set(data.matched_keywords))[:6])
        kw_line = f"\nСовпали слова: {shown}"

    lines = [
        f"🔍 «{preset_label}» — {count} из {data.with_interest_total} "
        f"({_pct(count, data.with_interest_total)})",
        kw_line.strip(),
        "",
        "👤 Пользователи:",
    ]

    for user in data.users[:preview_limit]:
        preview = (user.interest_query or "").strip().replace("\n", " ")
        if len(preview) > 70:
            preview = preview[:67] + "…"
        lines.append(f"  • {_format_user_ref(user)} — «{preview}»")

    if count > preview_limit:
        lines.append(f"  … и ещё {count - preview_limit}")

    lines.append("\nСводка: /interests")
    return "\n".join(line for line in lines if line is not None)

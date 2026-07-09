import json
import re

from db.models import CatalogOpportunity

OPPORTUNITY_TYPES = (
    "грант",
    "стипендия",
    "хакатон",
    "стажировка",
    "конкурс",
    "олимпиада",
    "эссе",
    "кейс",
    "летняя_школа",
    "курс",
    "мероприятие",
    "зритель",
    "другое",
)

CATEGORY_DISPLAY: dict[str, tuple[str, str]] = {
    "грант": ("💰", "Гранты"),
    "стипендия": ("🎓", "Стипендии"),
    "хакатон": ("💻", "Хакатоны"),
    "стажировка": ("🏢", "Стажировки"),
    "конкурс": ("🏆", "Конкурсы"),
    "олимпиада": ("🥇", "Олимпиады"),
    "эссе": ("✍️", "Конкурсы эссе"),
    "кейс": ("📋", "Кейс-чемпионаты"),
    "летняя_школа": ("☀️", "Летние школы"),
    "курс": ("📚", "Курсы"),
    "мероприятие": ("📅", "Мероприятия"),
    "зритель": ("👀", "Зрителю"),
}

CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "стипендия": (
        "стипенди",
        "scholarship",
        "mext",
        "обучени",
        "учёб",
        "учеб",
        "university",
        "магистр",
        "бакалавр",
    ),
    "хакатон": (
        "хакатон",
        "hackathon",
        "hack ",
        "хак ",
        "datathon",
        "startup battle",
        "стартап battle",
        "стартап-батл",
        "pitch battle",
        "pitch day",
        "demo day",
        "launchzone",
        "питчинг",
    ),
    "грант": ("грант", "grant", "фонд", "foundation"),
    "стажировка": ("стажиров", "internship", "intern ", "trainee", "практик"),
    "олимпиада": (
        "олимпиад",
        "olympiad",
        "olympics",
        "imo ",
        "ioi ",
        "icho",
        "ipho",
    ),
    "эссе": (
        "эссе",
        "essay",
        "конкурс эссе",
        "essay contest",
        "writing contest",
        "literary contest",
    ),
    "кейс": (
        "кейс-чемп",
        "case champ",
        "case competition",
        "бизнес-кейс",
        "case cup",
        "case study",
        "кейс чемп",
    ),
    "летняя_школа": (
        "летн",
        "summer school",
        "summer program",
        "summer camp",
        "летний camp",
        "летняя школа",
    ),
    "курс": (
        "курс",
        "courses",
        "course ",
        "программа обуч",
        "bootcamp",
        "буткемп",
        "летний курс",
        "обучающ",
    ),
    "конкурс": (
        "конкурс",
        "competition",
        "contest",
        "отбор",
        "challenge",
        "соревнован",
        "ивент",
    ),
    "мероприятие": (
        "митап",
        "meetup",
        "конферен",
        "воркшоп",
        "workshop",
        "саммит",
        "summit",
        "форум",
        "нетворк",
        "меропри",
        "лекци",
        "talk",
        "митап",
    ),
    "зритель": (
        "зрител",
        "для зрител",
        "посмотреть",
        "прийти на",
        "аудитор",
        "audience",
        "spectator",
        "посетител",
        "присутств",
    ),
}

_CUSTOM_TO_STANDARD: dict[str, str] = {
    "стажировки": "стажировка",
    "хакатоны": "хакатон",
    "гранты": "грант",
    "обучение": "стипендия",
    "зрителю": "зритель",
    "стартапы": "стартапы",
    "олимпиады": "олимпиада",
    "эссе конкурс": "эссе",
    "кейс-чемпионат": "кейс",
    "летняя школа": "летняя_школа",
    "курсы": "курс",
}

# Слабые ключи — сами по себе не добавляют вторую категорию (только если уже primary)
_WEAK_KEYWORDS: dict[str, frozenset[str]] = {
    "конкурс": frozenset({"стартап", "startup", "стартапер", "ивент", "акселератор", "incubator", "питч", "pitch"}),
    "грант": frozenset({"акселератор", "инкубатор"}),
    "мероприятие": frozenset({"talk", "лекци"}),
}

MAX_OPPORTUNITY_TAGS = 4

ALL_CATALOG_TYPES = [t for t in OPPORTUNITY_TYPES if t != "другое"]

_CONTEST_RELATED = ("хакатон", "кейс", "олимпиада", "эссе", "грант", "мероприятие")


def _keyword_in_text(keyword: str, text: str) -> bool:
    """Avoid «курс» matching inside «конкурсы»."""
    lowered = text.lower()
    kw = keyword.lower()
    if len(kw) <= 4:
        return bool(re.search(rf"(?<![\w]){re.escape(kw)}(?![\w])", lowered, flags=re.UNICODE))
    return kw in lowered

_TOPIC_ALIASES: dict[str, tuple[str, ...]] = {
    "стартапер": ("стартап", "startup", "start-up", "pitch", "питч", "акселератор", "ивент", "founder"),
    "стартап": ("startup", "pitch", "питч", "акселератор", "founder"),
    "startup": ("startup", "стартап", "pitch", "founder"),
    "стартапы": (
        "стартап",
        "startup",
        "start-up",
        "pitch",
        "питч",
        "founder",
        "фаундер",
        "акселератор",
        "accelerator",
        "incubator",
        "инкубатор",
        "entrepreneur",
        "предприним",
        "venture",
    ),
    "дизайн": ("design", "дизайн", "ux", "ui", "figma"),
    "эколог": ("эко", "ecology", "climate", "green", "устойчив"),
}

_STARTUP_BLOB_MARKERS: tuple[str, ...] = (
    "стартап",
    "startup",
    "start-up",
    "стартапер",
    "founder",
    "фаундер",
    "pitch",
    "питч",
    "акселератор",
    "accelerator",
    "incubator",
    "инкубатор",
    "entrepreneur",
    "предприним",
    "venture",
    "business plan",
    "бизнес-план",
    "demo day",
)

_STARTUP_DOMAIN_TAGS = frozenset({"стартапы", "стартап", "startup", "бизнес"})

_CUSTOM_TAG_RULES: tuple[tuple[str, str], ...] = (
    (r"олимпиад|olympiad", "олимпиады"),
    (r"эссе|essay contest|writing contest", "эссе"),
    (r"кейс-чемп|case champ|бизнес-кейс", "кейс"),
    (r"летн.{0,6}школ|summer school|summer program", "летняя школа"),
    (r"\bкурс|bootcamp|буткемп|course\b", "курсы"),
    (r"стартап|startup|стартапер|founder|фаундер|акселератор|accelerator|инкубатор|incubator", "стартапы"),
    (r"зрител|посмотреть|прийти на|audience|spectator", "зрителю"),
    (r"дизайн|design|ux|ui", "дизайн"),
    (r"эко|ecology|climate|green", "экология"),
    (r"it\b|tech|разработ|developer|программ", "IT"),
    (r"стипенди|scholarship|уч[её]б", "обучение"),
    (r"стажиров|intern", "стажировки"),
    (r"хакатон|hackathon", "хакатоны"),
    (r"грант|grant", "гранты"),
)


def extract_custom_tags(text: str) -> list[str]:
    lowered = text.lower()
    found: list[str] = []
    for pattern, label in _CUSTOM_TAG_RULES:
        if re.search(pattern, lowered, flags=re.I):
            if label not in found:
                found.append(label)
    return found


def _normalize_tag(tag: str) -> str:
    t = tag.lower().strip()
    return _CUSTOM_TO_STANDARD.get(t, t)


def _keyword_hits(category: str, text: str) -> tuple[bool, bool]:
    """(any_hit, strong_hit) for category in text."""
    lowered = text.lower()
    keywords = CATEGORY_KEYWORDS.get(category, ())
    weak = _WEAK_KEYWORDS.get(category, frozenset())
    strong_hit = False
    any_hit = False
    for kw in keywords:
        if not _keyword_in_text(kw, lowered):
            continue
        any_hit = True
        if kw not in weak:
            strong_hit = True
    return any_hit, strong_hit


def extract_opportunity_categories(text: str) -> list[str]:
    """Standard + custom categories with a clear keyword match in post text."""
    merged: list[str] = []
    for tag in extract_custom_tags(text):
        norm = _normalize_tag(tag)
        if norm in OPPORTUNITY_TYPES:
            if norm not in merged:
                merged.append(norm)
        elif tag not in merged:
            merged.append(tag)
    for category in CATEGORY_KEYWORDS:
        if category in merged:
            continue
        _, strong = _keyword_hits(category, text)
        if strong:
            merged.append(category)
    return merged[:MAX_OPPORTUNITY_TAGS]


def extract_categories_from_text(text: str) -> list[str]:
    """Типы возможностей + предметные области из запроса пользователя."""
    from services.interest_domains import extract_domains_from_text

    merged: list[str] = []
    for tag in extract_custom_tags(text):
        norm = _normalize_tag(tag)
        if norm not in merged:
            merged.append(norm)
    lowered = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if category in merged:
            continue
        if any(_keyword_in_text(keyword, lowered) for keyword in keywords):
            merged.append(category)
    for domain in extract_domains_from_text(text):
        if domain not in merged:
            merged.append(domain)
    return merged[:8]


_STOPWORDS = frozenset(
    """
    и в на с по для что это как я мы ты он она они меня мне мой моя мои
    the and for with from that this are was have has been will your you
    """.split()
)


def tags_to_json(tags: list[str]) -> str:
    return json.dumps(tags, ensure_ascii=False)


def parse_opportunity_tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(x).lower().strip() for x in data if x]
    except (json.JSONDecodeError, TypeError):
        pass
    return []


def entry_all_tags(entry: CatalogOpportunity) -> list[str]:
    parsed = parse_opportunity_tags(getattr(entry, "tags_json", None))
    if parsed:
        return parsed
    primary = (entry.opportunity_type or "другое").lower().strip()
    return [primary] if primary != "другое" else []


def build_opportunity_tags(
    source_text: str,
    *,
    title: str = "",
    description: str = "",
    requirements: str = "",
    primary_type: str,
    llm_tags: list[str] | None = None,
) -> list[str]:
    """One tag if only one category fits; 2–4 when the post clearly matches several."""
    from services.opportunity_type import is_startup_pitch_competition, is_viewer_or_audience_event

    blob = " ".join(filter(None, [source_text, title, description, requirements]))
    primary = _normalize_tag(primary_type or "другое")
    if primary == "другое":
        return []

    matched = extract_opportunity_categories(blob)
    lowered = blob.lower()

    tags: list[str] = []

    def add(tag: str) -> None:
        raw = tag.lower().strip()
        if not raw or raw == "другое":
            return
        norm = _normalize_tag(raw)
        canonical = norm if norm in OPPORTUNITY_TYPES else raw
        if canonical in tags:
            return
        tags.append(canonical)

    add(primary)
    for cat in matched:
        if cat != primary:
            add(cat)

    from services.interest_domains import extract_domains_from_text

    for domain in extract_domains_from_text(blob):
        add(domain)

    if isinstance(llm_tags, list):
        for item in llm_tags:
            add(str(item))

    if primary == "зритель" or is_viewer_or_audience_event(blob):
        if "конкурс" in tags and not any(
            marker in lowered
            for marker in (
                "подать заяв",
                "открыт набор",
                "прием заяв",
                "приём заяв",
                "принимаются заяв",
            )
        ):
            tags.remove("конкурс")

    if is_startup_pitch_competition(blob):
        if "конкурс" in tags:
            tags.remove("конкурс")
        if "стартапы" in tags:
            tags.remove("стартапы")
            tags.insert(0, "стартапы")

    # Только primary реально совпал — один тег
    if len(tags) <= 1:
        return [primary]

    return tags[:MAX_OPPORTUNITY_TAGS]


def is_standard_category(category: str) -> bool:
    return category.lower().strip() in OPPORTUNITY_TYPES


def resolve_catalog_types(categories: list[str]) -> list[str]:
    types, _extra = resolve_catalog_filter(categories)
    return types


def resolve_catalog_filter(categories: list[str]) -> tuple[list[str], list[str]]:
    """Standard types + domain/custom tags for catalog search (OR when both set)."""
    standard: list[str] = []
    extra: list[str] = []
    for cat in categories:
        if is_standard_category(cat):
            if cat not in standard:
                standard.append(cat)
        elif cat != "другое" and cat not in extra:
            extra.append(cat)

    if standard:
        types = list(standard)
        if "конкурс" in types:
            for rel in _CONTEST_RELATED:
                if rel not in types:
                    types.append(rel)
        if "стартапы" in extra or any(d in ("стартапы", "стартап", "startup") for d in extra):
            for rel in ("хакатон", "грант", "кейс", "конкурс", "мероприятие"):
                if rel not in types:
                    types.append(rel)
        return types, extra

    if extra:
        return list(ALL_CATALOG_TYPES), extra

    return list(ALL_CATALOG_TYPES), []


def _token_matches_blob(token: str, blob: str) -> bool:
    if token in blob:
        return True
    if len(token) >= 5 and token.endswith(("ы", "и", "а", "я", "е", "о", "у", "ю")):
        stem = token[:-1]
        if len(stem) >= 4 and stem in blob:
            return True
    return False


def _topic_aliases(token: str) -> tuple[str, ...]:
    return (token.lower(),) + _TOPIC_ALIASES.get(token.lower(), ())


def _interest_tokens(text: str) -> set[str]:
    tokens = {t for t in re.findall(r"[\w]{3,}", text.lower(), flags=re.UNICODE)}
    return tokens - _STOPWORDS


def _format_score(format_preferences: list[str], blob: str) -> float:
    """Слабый сигнал (+0.5 за совпадение, без штрафа за другой формат)."""
    if not format_preferences or len(format_preferences) >= 2:
        return 0.0
    want = format_preferences[0]
    online_markers = ("онлайн", "online", "дистанц", "remote", "zoom", "virtual")
    offline_markers = ("офлайн", "offline", "оффлайн", "очно", "очный", "offline")
    has_online = any(m in blob for m in online_markers)
    has_offline = any(m in blob for m in offline_markers)
    if want == "online" and has_online and not has_offline:
        return 0.5
    if want == "offline" and has_offline and not has_online:
        return 0.5
    return 0.0


_CASH_PRIZE_MARKERS = (
    "денежн",
    "cash prize",
    "prize money",
    "monetary",
    "призовой фонд",
    "призовые",
    "выигра",
    "награда",
    "₸",
    "тенге",
    " $",
    " usd",
    " eur",
    "€",
)


def _entry_has_cash_prize(blob: str) -> bool:
    lowered = (blob or "").lower()
    if "денежн" in lowered and "приз" in lowered:
        return True
    return any(marker in lowered for marker in _CASH_PRIZE_MARKERS)


def is_domain_category(category: str) -> bool:
    from services.interest_domains import all_known_domain_slugs

    return category.lower().strip() in all_known_domain_slugs()


def wants_startup_focus(categories: list[str], interest_query: str) -> bool:
    lowered = (interest_query or "").lower()
    if any(c in categories for c in ("стартапы", "стартап", "startup")):
        return True
    return any(
        marker in lowered
        for marker in (
            "стартап",
            "startup",
            "стартапер",
            "фаундер",
            "founder",
            "питч",
            "pitch",
            "акселератор",
            "incubator",
            "инкубатор",
        )
    )


def entry_startup_related(entry: CatalogOpportunity) -> bool:
    tags = {t.lower().strip() for t in entry_all_tags(entry)}
    if tags & _STARTUP_DOMAIN_TAGS:
        return True
    blob = " ".join(
        filter(
            None,
            [
                entry.title,
                entry.description,
                entry.requirements or "",
            ],
        )
    ).lower()
    return any(marker in blob for marker in _STARTUP_BLOB_MARKERS)


def tag_display(category: str) -> tuple[str, str]:
    from services.interest_domains import display_for_domain

    key = category.lower().strip()
    if key in CATEGORY_DISPLAY:
        return CATEGORY_DISPLAY[key]
    return display_for_domain(key)


def relevance_score(
    interest_query: str,
    entry: CatalogOpportunity,
    *,
    format_preferences: list[str] | None = None,
) -> float:
    tokens = _interest_tokens(interest_query)
    if not tokens:
        return 0.0

    blob = " ".join(
        filter(
            None,
            [
                entry.title,
                entry.description,
                entry.requirements or "",
                entry.opportunity_type,
                " ".join(entry_all_tags(entry)),
            ],
        )
    ).lower()

    score = 0.0
    matched = False
    for token in tokens:
        if _token_matches_blob(token, blob):
            score += 2.0 if len(token) >= 5 else 1.0
            matched = True
            continue
        for alias in _topic_aliases(token):
            if len(alias) >= 4 and alias in blob:
                score += 2.5
                matched = True
                break

    categories = extract_categories_from_text(interest_query)
    standard = [c for c in categories if is_standard_category(c)]
    domains = [c for c in categories if is_domain_category(c)]
    entry_tags = set(entry_all_tags(entry))
    if standard and entry_tags & set(standard):
        score += 3.0
    elif categories and entry_tags & set(categories):
        score += 2.0

    if standard and (entry.opportunity_type in standard or entry_tags & set(standard)):
        score = max(score, 3.5)

    if domains:
        domain_blob = blob
        domain_hits = sum(
            1
            for domain in domains
            if domain in domain_blob or any(alias in domain_blob for alias in _topic_aliases(domain))
        )
        if domain_hits:
            score += 1.5 + domain_hits * 0.5
        if "стартапы" in domains and entry_startup_related(entry):
            score += 5.0
        elif "стартапы" in domains:
            score *= 0.5
        if "денежные призы" in domains and _entry_has_cash_prize(blob):
            score += 2.0

    if wants_startup_focus(categories, interest_query) and entry_startup_related(entry):
        score += 4.0
    elif wants_startup_focus(categories, interest_query):
        score *= 0.45

    if format_preferences:
        score += _format_score(format_preferences, blob)

    # Стартаперу ищущему конкурсы — не подсовываем «прийти зрителем»
    if entry.opportunity_type == "зритель" or "зритель" in entry_tags:
        wants_viewer = any(
            kw in (interest_query or "").lower()
            for kw in ("зрител", "посмотреть", "прийти", "аудитор", "посет")
        )
        if not wants_viewer and "зритель" not in standard and "зрителю" not in categories:
            score *= 0.35

    if not matched and score < 2.0:
        return 0.0
    return score


def rank_for_user(
    interest_query: str,
    items: list[CatalogOpportunity],
    *,
    limit: int = 5,
    min_score: float = 3.0,
    format_preferences: list[str] | None = None,
) -> list[CatalogOpportunity]:
    if not items:
        return []

    from llm.spam_filter import is_likely_interview_or_rubric, is_likely_spam_or_ad

    scored: list[tuple[float, CatalogOpportunity]] = []
    for item in items:
        blob = " ".join(
            filter(None, [item.title, item.description, item.requirements, interest_query])
        )
        raw = ""
        if getattr(item, "raw_message", None) and getattr(item.raw_message, "text", None):
            raw = item.raw_message.text
        source = raw or blob
        if is_likely_spam_or_ad(source)[0] or is_likely_interview_or_rubric(source)[0]:
            continue
        score = relevance_score(interest_query, item, format_preferences=format_preferences)
        if score >= min_score:
            scored.append((score, item))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored[:limit]]


def categories_to_json(categories: list[str]) -> str:
    return json.dumps(categories, ensure_ascii=False)


def user_matches_type(
    interest_query: str,
    saved_categories_json: str | None,
    opportunity_type: str,
    opportunity_tags: list[str] | None = None,
) -> bool:
    categories = []
    if saved_categories_json:
        try:
            data = json.loads(saved_categories_json)
            if isinstance(data, list):
                categories = [str(x).lower() for x in data]
        except (json.JSONDecodeError, TypeError):
            pass
    if not categories:
        categories = extract_categories_from_text(interest_query or "")
    standard = [c for c in categories if is_standard_category(c)]
    domains = [c for c in categories if is_domain_category(c)]
    entry_tags = {opportunity_type.lower()}
    if opportunity_tags:
        entry_tags |= {t.lower() for t in opportunity_tags}
    if standard:
        return bool(entry_tags & set(standard))
    if domains:
        return True
    if categories:
        return bool(entry_tags & set(categories))
    return True

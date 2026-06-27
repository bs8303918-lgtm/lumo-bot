import re

# Telegram / РКН маркеры рекламы
_AD_MARKERS = (
    "#реклама",
    "#reklama",
    "#ad",
    "#advert",
    "#sponsored",
    "реклама.",
    "реклама ",
    " erid:",
    " erid ",
    " erid\n",
    "информация о рекламодателе",
    "рекламодатель:",
)

# Типичный спам, не связанный с возможностями Lumo
_SPAM_PATTERNS = (
    re.compile(r"опрос[ыа]?\s+.{0,40}(?:kzt|тг|тенге|₸|руб|рубл)", re.I),
    re.compile(r"(?:заработ|выплат[аы]).{0,30}(?:смартфон|телефон|kzt|тг|₸)", re.I),
    re.compile(r"focus5g\.com", re.I),
    re.compile(r"начать\s+опрос", re.I),
    re.compile(r"честн[а-я]*\s+оценк[а-я]*\s+товар", re.I),
    re.compile(r"казино|ставк[аи]\s+на\s+спорт|forex|крипт[ао].{0,20}заработ", re.I),
    re.compile(r"подпис[ыа]вайся\s+на\s+канал.{0,20}(?:скидк|промо)", re.I),
)

# Слова, которые сами по себе не спам, но в связке с маркером рекламы — отсекаем
_OPPORTUNITY_HINTS = (
    "хакатон",
    "hackathon",
    "стипенди",
    "грант",
    "стажиров",
    "internship",
    "акселератор",
    "incubator",
    "pitch",
    "питч",
    "конкурс",
    "мероприят",
    "mitap",
    "митап",
    "воркшоп",
    "workshop",
    "отбор",
    "program",
    "программ",
    "scholarship",
    "grant",
    "startup",
    "стартап",
)

# Вопросы в групповых чатах — не объявления о возможностях
_CHAT_QUESTION_PATTERNS = (
    re.compile(r"кто\s*(?:[-\s])?(?:то|нибудь|нибудь)\s*(?:знает|подскаж|может|знает)", re.I),
    re.compile(r"кто\s+знает", re.I),
    re.compile(r"знает\s+ли\s+кто", re.I),
    re.compile(r"может\s+кто\s+(?:знает|подскаж)", re.I),
    re.compile(r"подскаж(ите|и|ьте|ь)", re.I),
    re.compile(r"посоветуй(те|ьте)", re.I),
    re.compile(r"есть\s+ли\s+у\s+(?:кого|вас|кого-нибудь)", re.I),
    re.compile(r"does\s+anyone\s+know", re.I),
    re.compile(r"anyone\s+know", re.I),
    re.compile(r"who\s+knows", re.I),
    re.compile(r"can\s+someone\s+(?:recommend|suggest)", re.I),
    re.compile(r"^.{0,40}(?:ребят|ребя|guys|hey)\s*[,!.]?\s*(?:кто|who|anyone)", re.I | re.M),
)

_ANNOUNCEMENT_SIGNALS = (
    "регистрац",
    "register",
    "apply",
    "подать заяв",
    "deadline",
    "дедлайн",
    "до ",
    "http",
    "t.me/",
    "форм",
    "отбор",
    "приглаша",
    "announce",
    "набор",
    "участник",
    "prize",
    "приз",
    "наград",
)

_LLM_META_DESCRIPTION_MARKERS = (
    "пользователь ищет",
    "автор ищет",
    "автор спрашивает",
    "пользователь спрашивает",
    "ищет информацию",
    "просит подсказать",
    "задаёт вопрос",
    "задает вопрос",
    "спрашивает о",
    "question about",
    "looking for information",
)


def is_likely_results_news(text: str) -> tuple[bool, str | None]:
    """News about winners/results lists — not an open call to apply."""
    if not text or len(text.strip()) < 20:
        return False, None

    lowered = text.lower()

    strong_markers = (
        "опубликованы списки",
        "опубликован список",
        "списки обладателей",
        "список обладателей",
        "стали обладателями",
        "стали победителями",
        "одобрила результаты",
        "одобрил результаты",
        "результаты конкурса",
        "итоги конкурса",
        "итоги отбора",
        "список победителей",
        "списки победителей",
        "поздравляем победит",
        "поздравляем обладател",
        "lists of winners",
        "winners announced",
        "results of the competition",
        "scholarship recipients",
    )
    if any(marker in lowered for marker in strong_markers):
        return True, "results_news"

    apply_hints = (
        "подать заяв",
        "прием заяв",
        "приём заяв",
        "регистрац",
        "register",
        "apply now",
        "deadline",
        "дедлайн",
        "набор продолж",
        "принимаются заяв",
        "подайте заяв",
    )
    if "списк" in lowered and any(w in lowered for w in ("обладател", "победител", "лауреат")):
        if not any(h in lowered for h in apply_hints):
            return True, "results_news"

    return False, None


def is_likely_digest_or_roundup(text: str) -> tuple[bool, str | None]:
    """Подборки, YouTube-дайджесты, списки ивентов — не одна конкретная возможность."""
    if not text or len(text.strip()) < 15:
        return False, None

    lowered = text.lower()

    if "youtube.com" in lowered or "youtu.be" in lowered:
        return True, "youtube_digest"

    digest_markers = (
        "список стартап",
        "стартап-ивент",
        "ивенты на остаток",
        "ивенты на конец",
        "на остаток июня",
        "на конец июня",
        "подборка на неделю",
        "дайджест",
        "подписки, лайк, колокольчик",
        "подписки лайк колокольчик",
        "актуальные ивенты",
        "мероприятия на неделю",
    )
    for marker in digest_markers:
        if marker in lowered:
            return True, "digest_roundup"

    if re.search(r"список.{0,30}(?:ивент|мероприят|хакатон|конкурс)", lowered):
        return True, "digest_roundup"

    return False, None


def is_likely_chat_question(text: str) -> tuple[bool, str | None]:
    """Вопрос в чате («кто знает…»), а не объявление о конкурсе/гранте."""
    if not text or len(text.strip()) < 10:
        return False, None

    stripped = text.strip()
    lowered = stripped.lower()

    for pattern in _CHAT_QUESTION_PATTERNS:
        if pattern.search(stripped):
            if not _has_announcement_signal(lowered):
                return True, "chat_question"

    if stripped.endswith("?") and not _has_announcement_signal(lowered):
        if any(w in lowered for w in ("кто", "где", "как найти", "подскаж", "знает", "anyone", "who knows")):
            return True, "question_mark"

    return False, None


def _has_announcement_signal(lowered_text: str) -> bool:
    return any(signal in lowered_text for signal in _ANNOUNCEMENT_SIGNALS)


from llm.json_utils import coerce_llm_dict


def is_invalid_opportunity_extraction(data, source_text: str) -> tuple[bool, str | None]:
    """Отсечь ошибочную классификацию (LLM принял вопрос или новость за объявление)."""
    data = coerce_llm_dict(data)
    if not data or not data.get("is_opportunity"):
        return False, None

    is_news, news_reason = is_likely_results_news(source_text)
    if is_news:
        return True, news_reason

    is_digest, digest_reason = is_likely_digest_or_roundup(source_text)
    if is_digest:
        return True, digest_reason

    is_question, q_reason = is_likely_chat_question(source_text)
    if is_question:
        return True, q_reason

    title = (data.get("title") or "").strip().lower()
    description = (data.get("description") or "").strip().lower()

    for marker in _LLM_META_DESCRIPTION_MARKERS:
        if marker in description:
            return True, "llm_meta_description"

    if title in ("возможность", "—", "-", "null", "") and not data.get("application_url"):
        if any(marker in description for marker in _LLM_META_DESCRIPTION_MARKERS):
            return True, "vague_title"
        if is_question:
            return True, "vague_title_question"

    return False, None


def is_likely_spam_or_ad(text: str) -> tuple[bool, str | None]:
    """Быстрая проверка до LLM. Возвращает (is_spam, reason)."""
    if not text or len(text.strip()) < 15:
        return False, None

    is_question, reason = is_likely_chat_question(text)
    if is_question:
        return True, reason

    is_news, news_reason = is_likely_results_news(text)
    if is_news:
        return True, news_reason

    is_digest, digest_reason = is_likely_digest_or_roundup(text)
    if is_digest:
        return True, digest_reason

    lowered = text.lower()

    for marker in _AD_MARKERS:
        if marker in lowered:
            if not _has_opportunity_signal(lowered):
                return True, "ad_marker"

    for pattern in _SPAM_PATTERNS:
        if pattern.search(text):
            return True, "spam_pattern"

    return False, None


def _has_opportunity_signal(lowered_text: str) -> bool:
    return any(hint in lowered_text for hint in _OPPORTUNITY_HINTS)

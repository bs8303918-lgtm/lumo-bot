"""Category extraction and relevance scoring — same logic as lumo-bot interest_matcher."""

from __future__ import annotations

import re

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
    "хакатон": ("хакатон", "hackathon", "hack ", "хак ", "datathon"),
    "грант": ("грант", "grant", "фонд", "foundation", "акселератор", "инкубатор"),
    "стажировка": ("стажиров", "internship", "intern ", "trainee", "практик"),
    "конкурс": (
        "конкурс",
        "competition",
        "contest",
        "отбор",
        "pitch",
        "pitching",
        "challenge",
        "соревнован",
        "olympiad",
        "олимпиад",
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
    ),
}

_STOPWORDS = frozenset(
    """
    и в на с по для что это как я мы ты он она они меня мне мой моя мои
    the and for with from that this are was have has been will your you
    """.split()
)


def extract_categories_from_text(text: str) -> list[str]:
    lowered = text.lower()
    found: list[str] = []
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            found.append(category)
    if found:
        return found
    return ["конкурс", "грант", "стипендия", "хакатон", "стажировка", "мероприятие"]


def _interest_tokens(text: str) -> set[str]:
    tokens = {t for t in re.findall(r"[\w]{3,}", text.lower(), flags=re.UNICODE)}
    return tokens - _STOPWORDS


def relevance_score(interest_query: str, entry) -> float:
    tokens = _interest_tokens(interest_query)
    if not tokens:
        return 0.0

    blob = " ".join(
        filter(
            None,
            [entry.title, entry.description, entry.requirements or "", entry.opportunity_type],
        )
    ).lower()

    score = 0.0
    for token in tokens:
        if token in blob:
            score += 2.0 if len(token) >= 5 else 1.0

    categories = extract_categories_from_text(interest_query)
    if entry.opportunity_type in categories:
        score += 3.0

    return score

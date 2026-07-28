"""Normalize target-country labels for catalog opportunities."""

from __future__ import annotations

import re

DEFAULT_COUNTRY = "Глобальная"

_GLOBAL_MARKERS = (
    "global",
    "worldwide",
    "international",
    "anywhere",
    "all countries",
    "любая стран",
    "для всех",
    "все стран",
    "международн",
    "worldwide",
    "глобал",
)

_ALIASES: list[tuple[tuple[str, ...], str]] = [
    (("казахстан", "kazakhstan", "қазақстан", "kz", "рк"), "Казахстан"),
    (("кыргызстан", "киргиз", "kyrgyz", "kg", "кыргыз"), "Кыргызстан"),
    (("узбекистан", "uzbekistan", "uz", "ўзбекистон"), "Узбекистан"),
    (("росси", "russia", "rf", "рф"), "Россия"),
    (("украин", "ukraine", "ua"), "Украина"),
    (("беларус", "belarus", "by"), "Беларусь"),
    (("таджикистан", "tajikistan", "tj"), "Таджикистан"),
    (("туркменистан", "turkmenistan", "tm"), "Туркменистан"),
    (("армен", "armenia", "am"), "Армения"),
    (("азербайджан", "azerbaijan", "az"), "Азербайджан"),
    (("грузи", "georgia", "ge"), "Грузия"),
    (("турци", "turkey", "türkiye", "tr"), "Турция"),
    (("коре", "korea", "kr"), "Корея"),
    (("япони", "japan", "jp"), "Япония"),
    (("китай", "china", "cn"), "Китай"),
    (("сша", "usa", "united states", "america", "us"), "США"),
    (("герман", "germany", "deutschland", "de"), "Германия"),
    (("франци", "france", "fr"), "Франция"),
    (("великобритан", "britain", "uk", "england"), "Великобритания"),
    (("оаэ", "uae", "emirates", "дубай", "dubai"), "ОАЭ"),
    (("сингапур", "singapore", "sg"), "Сингапур"),
    (("европ", "eu", "european"), "Европа"),
    (("снг", "cis"), "СНГ"),
    (("центральн ази", "central asia"), "Центральная Азия"),
]

_CHANNEL_HINTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?:^|[^a-z])kz(?:$|[^a-z])|kazakhstan|myextrakz|digitalbussinesskz|astana|jasa", re.I), "Казахстан"),
    (re.compile(r"(?:^|[^a-z])kg(?:$|[^a-z])|kyrgyz|kgworkzone", re.I), "Кыргызстан"),
    (re.compile(r"(?:^|[^a-z])uz(?:$|[^a-z])|uzbekistan|uz_grants", re.I), "Узбекистан"),
]


def _looks_global(text: str) -> bool:
    lower = text.lower().strip()
    return any(marker in lower for marker in _GLOBAL_MARKERS)


def normalize_country(value: str | None, *, fallback: str | None = None) -> str:
    """Map free-form LLM/channel text to a short display country label."""
    text = (value or "").strip()
    if not text or text.lower() in {"null", "none", "n/a", "-", "—"}:
        return normalize_country(fallback) if fallback else DEFAULT_COUNTRY

    if _looks_global(text):
        return DEFAULT_COUNTRY

    lower = text.lower()
    for aliases, label in _ALIASES:
        if any(alias in lower for alias in aliases):
            return label

    # Keep a short custom label (e.g. "Польша") instead of dumping a sentence.
    cleaned = re.sub(r"\s+", " ", text).strip(" .|,;")
    if 1 <= len(cleaned) <= 40 and "\n" not in cleaned:
        return cleaned[:1].upper() + cleaned[1:]

    return normalize_country(fallback) if fallback else DEFAULT_COUNTRY


def country_from_channel(channel_identifier: str | None, channel_title: str | None = None) -> str | None:
    blob = " ".join(filter(None, [channel_identifier or "", channel_title or ""]))
    if not blob:
        return None
    for pattern, label in _CHANNEL_HINTS:
        if pattern.search(blob):
            return label
    return None


def resolve_catalog_country(
    llm_value: str | None,
    *,
    channel_identifier: str | None = None,
    channel_title: str | None = None,
    title: str | None = None,
    description: str | None = None,
    requirements: str | None = None,
) -> str:
    """Prefer LLM country; else infer from text/channel; else global."""
    channel_hint = country_from_channel(channel_identifier, channel_title)
    text_blob = " ".join(filter(None, [title or "", description or "", requirements or ""]))
    text_hint = None
    if text_blob:
        normalized_from_text = normalize_country(text_blob, fallback=None)
        # Only treat text as a hint when it matched a known alias, not a free-form dump.
        if normalized_from_text != DEFAULT_COUNTRY or _looks_global(text_blob):
            # Re-check: normalize_country on long text may return DEFAULT via global markers
            # or a known alias. Avoid treating arbitrary long text as a country name.
            lower = text_blob.lower()
            if _looks_global(text_blob):
                text_hint = DEFAULT_COUNTRY
            else:
                for aliases, label in _ALIASES:
                    if any(alias in lower for alias in aliases):
                        text_hint = label
                        break

    if llm_value and str(llm_value).strip():
        return normalize_country(str(llm_value), fallback=text_hint or channel_hint)

    if text_hint:
        return text_hint
    if channel_hint:
        return channel_hint
    return DEFAULT_COUNTRY

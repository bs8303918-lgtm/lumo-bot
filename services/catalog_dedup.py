import re

from db.repositories.users import normalize_application_url

GENERIC_TITLES = frozenset(
    {
        "хакатон",
        "конкурс",
        "грант",
        "стипендия",
        "стажировка",
        "мероприятие",
        "возможность",
        "—",
        "-",
    }
)

_URL_RE = re.compile(r"https?://[^\s<>\"']+", re.I)


def normalize_catalog_title(title: str | None) -> str:
    if not title:
        return ""
    text = re.sub(r"\s+", " ", title.lower().strip())
    text = text.strip("«»\"'")
    return text


def is_specific_title(title: str | None) -> bool:
    norm = normalize_catalog_title(title)
    return len(norm) >= 8 and norm not in GENERIC_TITLES


def extract_urls_from_text(text: str | None) -> list[str]:
    if not text:
        return []
    urls = []
    for raw in _URL_RE.findall(text):
        norm = normalize_application_url(raw.rstrip(".,;)"))
        if norm:
            urls.append(norm)
    return urls


def catalog_dedupe_keys(title: str | None, application_url: str | None, description: str | None) -> set[str]:
    keys: set[str] = set()
    try:
        norm_title = normalize_catalog_title(title)
        if is_specific_title(norm_title):
            keys.add(f"title:{norm_title}")
        norm_app = normalize_application_url(application_url)
        if norm_app:
            keys.add(f"url:{norm_app}")
        for url in extract_urls_from_text(description):
            keys.add(f"url:{url}")
    except (ValueError, TypeError):
        pass
    return keys

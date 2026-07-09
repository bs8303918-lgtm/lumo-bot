"""Нормализация URL для Telegram-кнопок."""

from __future__ import annotations

_PLACEHOLDER_HOST_FRAGMENTS = (
    "your-app.vercel.app",
    "your-service.up.railway.app",
    "startify.example",
    "example.com",
    "localhost",
    "127.0.0.1",
)


def normalize_https_url(url: str) -> str:
    text = (url or "").strip()
    if not text:
        return ""
    if text.startswith("@"):
        return f"https://t.me/{text.lstrip('@')}"
    if text.startswith("t.me/") or text.startswith("telegram.me/"):
        return f"https://{text}"
    if not text.startswith("http://") and not text.startswith("https://"):
        return f"https://{text.lstrip('/')}"
    if text.startswith("http://"):
        return f"https://{text[len('http://'):]}"
    return text


def is_valid_telegram_button_url(url: str) -> bool:
    normalized = normalize_https_url(url)
    if not normalized.startswith("https://"):
        return False
    if is_placeholder_url(normalized):
        return False
    lowered = normalized.lower()
    if "t.me/" in lowered or "telegram.me/" in lowered:
        return len(normalized) > len("https://t.me/")
    host = normalized.split("://", 1)[-1].split("/", 1)[0]
    return bool(host and "." in host)


def is_valid_webapp_url(url: str) -> bool:
    normalized = normalize_https_url(url)
    if not normalized.startswith("https://"):
        return False
    if is_placeholder_url(normalized):
        return False
    # Railway /app — не Mini App на Vercel; Telegram часто отвечает URL_INVALID
    if "railway.app" in normalized and normalized.rstrip("/").endswith("/app"):
        return False
    host = normalized.split("://", 1)[-1].split("/", 1)[0]
    return bool(host and "." in host)


def is_placeholder_url(url: str) -> bool:
    lowered = normalize_https_url(url).lower()
    return any(fragment in lowered for fragment in _PLACEHOLDER_HOST_FRAGMENTS)


def safe_button_url(url: str) -> str:
    normalized = normalize_https_url(url)
    return normalized if is_valid_telegram_button_url(normalized) else ""


def safe_webapp_url(url: str) -> str:
    normalized = normalize_https_url(url)
    return normalized if is_valid_webapp_url(normalized) else ""

"""Нормализация URL для Telegram-кнопок."""

from __future__ import annotations


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
    return text


def is_valid_telegram_button_url(url: str) -> bool:
    if not url.startswith("https://"):
        return False
    lowered = url.lower()
    if "t.me/" in lowered or "telegram.me/" in lowered:
        return len(url) > len("https://t.me/")
    return "://" in url and "." in url.split("://", 1)[-1]


def is_valid_webapp_url(url: str) -> bool:
    if not url.startswith("https://"):
        return False
    if "railway.app" in url and url.rstrip("/").endswith("/app"):
        return False
    return True

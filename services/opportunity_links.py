"""Normalize and validate opportunity URLs for Mini App / bot."""

from __future__ import annotations

import re

_INVALID_HOSTS = frozenset({"example.com", "example.org", "localhost"})
_TME_RE = re.compile(r"(?:https?://)?t\.me/[^\s]+", re.I)


def normalize_message_link(link: str | None) -> str | None:
    if not link:
        return None
    text = link.strip()
    if not text or text in {"—", "-"}:
        return None
    if text.startswith("lumo://"):
        return None
    if text.startswith("@"):
        handle = text[1:].split("/")[0]
        return f"https://t.me/{handle}" if handle else None
    if text.lower().startswith("t.me/"):
        return f"https://{text}"
    if "t.me/" in text.lower() and not text.lower().startswith("http"):
        return f"https://{text.lstrip('/')}"
    if text.lower().startswith("http"):
        if "t.me/" in text.lower() or "telegram.me/" in text.lower():
            return text.split()[0]
        return None
    return None


def normalize_application_url(url: str | None) -> str | None:
    if not url:
        return None
    text = url.strip()
    if not text or text in {"—", "-", "none", "null"}:
        return None
    if text.startswith("lumo://"):
        return None
    lower = text.lower()
    if not lower.startswith("http"):
        if lower.startswith("t.me/") or lower.startswith("@") or "t.me/" in lower:
            return normalize_message_link(text)
        return None
    for host in _INVALID_HOSTS:
        if host in lower:
            return None
    if "t.me/" in lower or "telegram.me/" in lower:
        return normalize_message_link(text)
    return text.split()[0]


def pick_telegram_post_link(message_link: str | None, application_url: str | None) -> str | None:
    for candidate in (message_link, application_url):
        normalized = normalize_message_link(candidate) if candidate and "t.me" in candidate.lower() else None
        if normalized and "/" in normalized.rstrip("/").split("t.me/", 1)[-1]:
            return normalized
    return normalize_message_link(message_link) or normalize_message_link(application_url)


def channel_public_url(channel_identifier: str | None) -> str | None:
    ident = (channel_identifier or "").strip().lstrip("@")
    if not ident or ident.startswith("-") or ident.isdigit():
        return None
    return f"https://t.me/{ident}"


def build_message_link_from_parts(channel_identifier: str | None, telegram_message_id: int | None) -> str | None:
    ident = (channel_identifier or "").strip().lstrip("@")
    if not ident or ident.startswith("-") or not telegram_message_id:
        return None
    return f"https://t.me/{ident}/{int(telegram_message_id)}"


def extract_registration_url(*texts: str | None) -> str | None:
    from monitor.channel_resolver import ChannelResolver

    for text in texts:
        if not text:
            continue
        for raw in ChannelResolver.extract_urls(text):
            normalized = normalize_application_url(raw)
            if normalized and "t.me" not in normalized.lower():
                return normalized
    return None


def enrich_opportunity_links(
    payload: dict,
    *,
    channel_identifier: str | None = None,
    telegram_message_id: int | None = None,
    description: str | None = None,
    requirements: str | None = None,
) -> dict:
    if not payload.get("messageLink"):
        built = build_message_link_from_parts(channel_identifier, telegram_message_id)
        if built:
            payload["messageLink"] = built
    channel_url = channel_public_url(channel_identifier)
    if channel_url:
        payload["channelUrl"] = channel_url
    if not payload.get("applicationUrl"):
        found = extract_registration_url(description, requirements)
        if found:
            payload["applicationUrl"] = found
            payload["isPremium"] = True
    return payload

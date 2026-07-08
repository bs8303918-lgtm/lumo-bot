"""Verify Google Sign-In ID tokens for the Lumo web app."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import httpx

from config import get_settings


@dataclass(frozen=True)
class GoogleUser:
    sub: str
    email: str | None
    name: str | None
    picture: str | None


def google_telegram_id(sub: str) -> int:
    """Stable synthetic telegram_id for Google-only accounts (negative range)."""
    digest = hashlib.sha256(sub.encode()).hexdigest()
    offset = int(digest[:15], 16) % 8_000_000_000_000_000
    return -(9_000_000_000_000_000 + offset)


async def verify_google_id_token(id_token: str) -> GoogleUser | None:
    settings = get_settings()
    client_id = settings.google_oauth_client_id.strip()
    if not client_id or not id_token.strip():
        return None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"id_token": id_token.strip()},
            )
        if res.status_code != 200:
            return None
        data = res.json()
    except (httpx.HTTPError, ValueError):
        return None

    aud = data.get("aud") or data.get("azp")
    if aud != client_id:
        return None

    sub = data.get("sub")
    if not sub:
        return None

    return GoogleUser(
        sub=str(sub),
        email=data.get("email") or None,
        name=data.get("name") or None,
        picture=data.get("picture") or None,
    )

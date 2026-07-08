"""Verify Telegram Login Widget callback (https://core.telegram.org/widgets/login)."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class TelegramLoginUser:
    id: int
    username: str | None


def verify_login_payload(data: dict, bot_token: str, *, max_age_sec: int = 86400 * 7) -> int | None:
    payload = {k: str(v) for k, v in data.items() if k != "hash" and v is not None}
    check_hash = data.get("hash")
    if not check_hash or "id" not in payload or "auth_date" not in payload:
        return None

    try:
        auth_date = int(payload["auth_date"])
    except (TypeError, ValueError):
        return None

    if time.time() - auth_date > max_age_sec:
        return None

    check_string = "\n".join(f"{k}={payload[k]}" for k in sorted(payload))
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    calculated = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
    if calculated != str(check_hash):
        return None

    return int(payload["id"])


def parse_login_user(raw: str, bot_token: str) -> TelegramLoginUser | None:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None

    if not isinstance(data, dict):
        return None

    telegram_id = verify_login_payload(data, bot_token)
    if telegram_id is None:
        return None

    username = data.get("username")
    return TelegramLoginUser(id=telegram_id, username=str(username) if username else None)

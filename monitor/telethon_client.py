import asyncio
import logging
import sqlite3
from pathlib import Path

from telethon import TelegramClient
from telethon.errors import AuthKeyUnregisteredError, SessionPasswordNeededError
from telethon.sessions import StringSession

from config import get_settings

logger = logging.getLogger(__name__)

_client: TelegramClient | None = None


class TelethonCredentialsMissingError(ValueError):
    """API ID / Hash not set in environment (e.g. missing Railway Variables)."""


def telethon_credentials_configured() -> bool:
    settings = get_settings()
    return bool(settings.telegram_api_id and settings.telegram_api_hash.strip())


def uses_string_session() -> bool:
    return bool(get_settings().telethon_session_string.strip())


def prepare_telethon_session_path() -> Path:
    """Ensure session directory exists; fall back to /app/data on Railway if /data is missing."""
    settings = get_settings()
    path = settings.resolved_telethon_session_path
    parent = path.parent
    try:
        parent.mkdir(parents=True, exist_ok=True)
        return path
    except OSError:
        fallback = Path("/app/data/lumo_session")
        try:
            fallback.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise RuntimeError(
                f"Cannot create Telethon session directory ({parent} or {fallback.parent})"
            ) from exc
        logger.warning(
            "Telethon session dir %s unavailable — using %s. "
            "Prefer TELETHON_SESSION_STRING in Railway Variables (see scripts/export_telethon_session.py).",
            parent,
            fallback,
        )
        return fallback


def _build_client(settings) -> TelegramClient:
    session_string = settings.telethon_session_string.strip()
    if session_string:
        logger.info("Telethon: using TELETHON_SESSION_STRING from env")
        return TelegramClient(
            StringSession(session_string),
            settings.telegram_api_id,
            settings.telegram_api_hash,
        )
    session_path = prepare_telethon_session_path()
    return TelegramClient(
        str(session_path),
        settings.telegram_api_id,
        settings.telegram_api_hash,
    )


def get_telethon_client() -> TelegramClient:
    global _client
    if _client is None:
        settings = get_settings()
        if not settings.telegram_api_id or not settings.telegram_api_hash.strip():
            raise TelethonCredentialsMissingError(
                "TELEGRAM_API_ID и TELEGRAM_API_HASH не заданы. "
                "На Railway: сервис lumo-bot → Variables → добавьте обе переменные → Redeploy."
            )
        _client = _build_client(settings)
    return _client


def reset_client() -> None:
    global _client
    _client = None


async def ensure_telethon_connected() -> TelegramClient:
    client = get_telethon_client()
    try:
        if not client.is_connected():
            for attempt in range(5):
                try:
                    await client.connect()
                    break
                except sqlite3.OperationalError as exc:
                    if uses_string_session() or "database is locked" not in str(exc).lower() or attempt == 4:
                        raise
                    wait = 0.5 * (attempt + 1)
                    logger.warning(
                        "Telethon session locked (attempt %d/5), retry in %.1fs — "
                        "stop duplicate main.py if this persists",
                        attempt + 1,
                        wait,
                    )
                    await asyncio.sleep(wait)
        if not await client.is_user_authorized():
            logger.warning(
                "Telethon не залогинен. Локально: python scripts/telethon_login_qr.py && "
                "python scripts/export_telethon_session.py → TELETHON_SESSION_STRING в Railway"
            )
    except AuthKeyUnregisteredError:
        logger.error(
            "Сессия Telethon повреждена. Сгенерируй новую: telethon_login_qr.py → export_telethon_session.py"
        )
        reset_client()
        raise
    return client


async def telethon_is_authorized() -> bool:
    try:
        client = get_telethon_client()
        if not client.is_connected():
            await client.connect()
        return await client.is_user_authorized()
    except AuthKeyUnregisteredError:
        return False
    except Exception:
        return False


async def require_authorized_client() -> TelegramClient | None:
    """Возвращает клиент только если сессия валидна и пользователь залогинен."""
    if not get_settings().telegram_api_id or not get_settings().telegram_api_hash:
        return None
    try:
        client = await ensure_telethon_connected()
        if await client.is_user_authorized():
            return client
    except (AuthKeyUnregisteredError, TelethonCredentialsMissingError):
        pass
    except (sqlite3.OperationalError, OSError, RuntimeError) as exc:
        logger.warning("Telethon unavailable: %s", exc)
    except Exception as exc:
        logger.warning("Telethon unavailable: %s", exc)
    return None


async def interactive_login(code: str, password: str | None = None) -> bool:
    settings = get_settings()
    client = get_telethon_client()
    await client.connect()
    try:
        await client.sign_in(settings.telegram_phone, code)
    except SessionPasswordNeededError:
        if not password:
            raise
        await client.sign_in(password=password)
    return await client.is_user_authorized()

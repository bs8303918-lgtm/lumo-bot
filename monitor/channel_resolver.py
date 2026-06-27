import logging
import re
from dataclasses import dataclass

from telethon import TelegramClient
from telethon.errors import (
    AuthKeyUnregisteredError,
    ChannelPrivateError,
    FloodWaitError,
    UsernameInvalidError,
    UsernameNotOccupiedError,
)
from telethon.tl.types import Channel

from config import get_settings
from db.repositories.users import is_valid_channel_format, normalize_channel_identifier
from logging_setup import log_error

logger = logging.getLogger(__name__)


@dataclass
class ChannelInfo:
    identifier: str
    title: str | None
    telegram_channel_id: int | None
    is_public: bool
    message_link_prefix: str


class ChannelResolver:
    def __init__(self, client: TelegramClient):
        self.client = client
        self.settings = get_settings()

    async def validate_public_channel(self, raw_input: str) -> tuple[ChannelInfo | None, str | None]:
        identifier = normalize_channel_identifier(raw_input)
        if not identifier or not is_valid_channel_format(identifier):
            return None, "Неверный формат. Пришли @username, например @startup_course_com"

        if not await self.client.is_user_authorized():
            return None, (
                "Telethon не залогинен. Администратору нужно выполнить:\n"
                "python scripts/reset_telethon_session.py\n"
                "python scripts/telethon_login.py"
            )

        try:
            entity = await self.client.get_entity(identifier)
        except AuthKeyUnregisteredError:
            return None, (
                "Сессия Telethon повреждена. Выполните на сервере:\n"
                "python scripts/reset_telethon_session.py\n"
                "python scripts/telethon_login.py"
            )
        except UsernameNotOccupiedError:
            return None, f"Канал @{identifier} не найден. Проверь username."
        except UsernameInvalidError:
            return None, "Некорректный username канала."
        except ChannelPrivateError:
            return None, (
                "Этот канал приватный или недоступен. Lumo мониторит только публичные "
                "Telegram-каналы с username (например @startup_course_com)."
            )
        except FloodWaitError as exc:
            log_error(logger, "channel_resolver", exc, {"seconds": exc.seconds, "channel": identifier})
            return None, f"Слишком много запросов к Telegram. Попробуй через {exc.seconds} сек."
        except Exception as exc:
            log_error(logger, "channel_resolver", exc, {"channel": identifier})
            return None, "Не удалось проверить канал. Попробуй позже."

        if not isinstance(entity, Channel):
            return None, "Это не канал. Пришли ссылку на публичный Telegram-канал."

        username = getattr(entity, "username", None)
        if self.settings.require_public_channels and not username:
            return None, (
                "Этот канал не публичный (нет username). Lumo мониторит только публичные каналы "
                "вида @startup_course_com."
            )

        title = getattr(entity, "title", None) or identifier
        link_prefix = f"https://t.me/{username or identifier}"
        return ChannelInfo(
            identifier=(username or identifier).lower(),
            title=title,
            telegram_channel_id=entity.id,
            is_public=bool(username),
            message_link_prefix=link_prefix,
        ), None

    @staticmethod
    def build_message_link(channel_identifier: str, message_id: int) -> str:
        return f"https://t.me/{channel_identifier}/{message_id}"

    @staticmethod
    def extract_urls(text: str) -> list[str]:
        return re.findall(r"https?://[^\s<>\"']+", text)

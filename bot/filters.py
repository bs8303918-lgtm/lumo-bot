from aiogram import F
from aiogram.filters import BaseFilter
from aiogram.types import Message

from config import get_settings


class AdminFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        if not message.from_user:
            return False
        return get_settings().is_admin(message.from_user.id)

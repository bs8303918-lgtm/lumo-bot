from fastapi import Depends, Header, HTTPException, status
from aiogram.utils.web_app import safe_parse_webapp_init_data
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db
from config import get_settings
from db.models import User
from db.repositories.users import UserRepository


async def get_current_user(
    x_telegram_init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
    x_dev_telegram_id: int | None = Header(default=None, alias="X-Dev-Telegram-Id"),
    session: AsyncSession = Depends(get_db),
) -> User:
    settings = get_settings()

    if x_telegram_init_data:
        if not settings.telegram_bot_token:
            raise HTTPException(status_code=503, detail="Bot token not configured")
        try:
            data = safe_parse_webapp_init_data(
                token=settings.telegram_bot_token,
                init_data=x_telegram_init_data,
            )
        except ValueError as exc:
            raise HTTPException(status_code=401, detail="Invalid init data") from exc
        user, _ = await UserRepository(session).get_or_create(data.user.id, data.user.username)
        return user

    if settings.api_allow_dev_auth and x_dev_telegram_id:
        user, _ = await UserRepository(session).get_or_create(x_dev_telegram_id, None)
        return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Open the app from Telegram or provide dev auth header",
    )


async def require_admin(user: User = Depends(get_current_user)) -> User:
    settings = get_settings()
    if not settings.is_admin(user.telegram_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user

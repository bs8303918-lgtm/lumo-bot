from fastapi import Depends, Header, HTTPException, status
from aiogram.utils.web_app import safe_parse_webapp_init_data
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db
from config import get_settings
from db.models import User
from db.repositories.users import UserRepository
from services.google_auth import google_telegram_id, verify_google_id_token
from services.telegram_login import parse_login_user
from services.web_auth import parse_web_token


async def get_current_user(
    authorization: str | None = Header(default=None),
    x_telegram_init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
    x_telegram_login_data: str | None = Header(default=None, alias="X-Telegram-Login-Data"),
    x_google_id_token: str | None = Header(default=None, alias="X-Google-Id-Token"),
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

    if x_telegram_login_data:
        if not settings.telegram_bot_token:
            raise HTTPException(status_code=503, detail="Bot token not configured")
        login_user = parse_login_user(x_telegram_login_data, settings.telegram_bot_token)
        if not login_user:
            raise HTTPException(status_code=401, detail="Invalid or expired Telegram login")
        user, _ = await UserRepository(session).get_or_create(login_user.id, login_user.username)
        return user

    if x_google_id_token:
        google_user = await verify_google_id_token(x_google_id_token)
        if not google_user:
            raise HTTPException(status_code=401, detail="Invalid or expired Google sign-in")
        user, created = await UserRepository(session).get_or_create_google(
            google_user.sub,
            google_telegram_id(google_user.sub),
            email=google_user.email,
            display_name=google_user.name,
        )
        if created:
            await session.commit()
        return user

    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        secret = (settings.web_auth_secret or settings.telegram_bot_token or "").strip()
        if not secret:
            raise HTTPException(status_code=503, detail="Web auth is not configured on server")
        user_id = parse_web_token(token, secret)
        if not user_id:
            raise HTTPException(status_code=401, detail="Сессия истекла — войди снова")
        user = await UserRepository(session).get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=401, detail="Сессия истекла — войди снова")
        return user

    if settings.api_allow_dev_auth and x_dev_telegram_id:
        user, _ = await UserRepository(session).get_or_create(x_dev_telegram_id, None)
        return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Войди, чтобы пользоваться Lumo",
    )


async def require_admin(user: User = Depends(get_current_user)) -> User:
    settings = get_settings()
    if not settings.user_is_admin(user.telegram_id, user.email):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user

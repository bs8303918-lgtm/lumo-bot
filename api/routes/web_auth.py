from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from api.deps import get_db
from config import get_settings
from db.models import User
from db.repositories.users import UserRepository
from services.web_auth import email_telegram_id, hash_password, issue_web_token, verify_password

router = APIRouter(tags=["web-auth"])


class RegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    name: str | None = Field(default=None, max_length=120)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        text = value.strip().lower()
        if "@" not in text or "." not in text.split("@")[-1]:
            raise ValueError("invalid email")
        return text


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


def _web_auth_secret() -> str:
    settings = get_settings()
    secret = (settings.web_auth_secret or settings.telegram_bot_token or "").strip()
    if not secret:
        raise HTTPException(status_code=503, detail="Web auth is not configured on server")
    return secret


def _token_response(user, token: str) -> dict:
    return {
        "token": token,
        "email": user.email,
        "name": user.display_name or (user.email.split("@")[0] if user.email else None),
    }


@router.post("/auth/register")
async def web_register(payload: RegisterRequest, session: AsyncSession = Depends(get_db)) -> dict:
    repo = UserRepository(session)
    email = payload.email.strip().lower()
    existing = await repo.get_by_email(email)
    if existing and existing.password_hash:
        raise HTTPException(status_code=409, detail="Аккаунт с этим email уже есть — войди")

    display_name = (payload.name or email.split("@")[0]).strip() or email.split("@")[0]
    password_hash = hash_password(payload.password)
    telegram_id = email_telegram_id(email)

    if existing:
        existing.password_hash = password_hash
        existing.display_name = display_name
        if not existing.email:
            existing.email = email
        user = existing
    else:
        user, _ = await repo.create_web_user(
            email=email,
            password_hash=password_hash,
            display_name=display_name,
            telegram_id=telegram_id,
        )

    await session.commit()
    token = issue_web_token(user.id, _web_auth_secret())
    return _token_response(user, token)


@router.post("/auth/login")
async def web_login(payload: LoginRequest, session: AsyncSession = Depends(get_db)) -> dict:
    repo = UserRepository(session)
    email = payload.email.strip().lower()
    user = await repo.get_by_email(email)
    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Неверный email или пароль")

    token = issue_web_token(user.id, _web_auth_secret())
    return _token_response(user, token)


class SetPasswordRequest(BaseModel):
    firstName: str = Field(min_length=1, max_length=60)
    lastName: str = Field(default="", max_length=60)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        text = value.strip().lower()
        if "@" not in text or "." not in text.split("@")[-1]:
            raise ValueError("invalid email")
        return text


@router.post("/auth/set-password")
async def web_set_password(
    payload: SetPasswordRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Let an already Telegram-authenticated Mini App user also log into the website.

    Attaches email/password to their existing account instead of creating a
    separate one, so /auth/login on the site resolves to the same user.
    """
    repo = UserRepository(session)
    existing = await repo.get_by_email(payload.email)
    if existing and existing.id != user.id:
        raise HTTPException(status_code=409, detail="Этот email уже используется другим аккаунтом")

    display_name = f"{payload.firstName.strip()} {payload.lastName.strip()}".strip()
    user.email = payload.email
    user.display_name = display_name or user.display_name
    user.password_hash = hash_password(payload.password)
    await session.commit()

    token = issue_web_token(user.id, _web_auth_secret())
    return _token_response(user, token)

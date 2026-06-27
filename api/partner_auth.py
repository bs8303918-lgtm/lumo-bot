"""Bearer auth for AI Startify (NestJS) server-to-server calls."""

from fastapi import Header, HTTPException, status

from config import get_settings


def require_partner_api_key(authorization: str | None = Header(default=None)) -> None:
    settings = get_settings()
    expected = settings.partner_api_key.strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Partner API is not configured (PARTNER_API_KEY)",
        )
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization")
    prefix = "Bearer "
    token = authorization[len(prefix) :] if authorization.startswith(prefix) else authorization
    if token != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid partner API key")

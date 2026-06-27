from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db
from api.schemas import ContactRequest, MessageResponse, PurchaseRequest
from config import get_settings
from db.repositories.catalog import LeadRepository
from services.admin_notify import notify_admin

router = APIRouter(prefix="/leads", tags=["leads"])


@router.post("/contact", response_model=MessageResponse)
async def submit_contact(
    payload: ContactRequest,
    session: AsyncSession = Depends(get_db),
) -> dict:
    await LeadRepository(session).create(
        contact=payload.contact.strip(),
        name=(payload.name or "").strip() or None,
        message=(payload.message or "").strip() or None,
        grant_id=payload.grantId,
        lead_type="contact",
    )
    settings = get_settings()
    grant_part = f" (грант #{payload.grantId})" if payload.grantId else ""
    await notify_admin(
        f"📩 Новая заявка{grant_part}\n"
        f"Контакт: {payload.contact}\n"
        f"Имя: {payload.name or '—'}\n"
        f"Сообщение: {payload.message or '—'}\n"
        f"Связаться: {settings.support_contact}"
    )
    return {"ok": True, "message": "Заявка принята. Мы свяжемся с вами в Telegram."}


@router.post("/purchase", response_model=MessageResponse)
async def submit_purchase(
    payload: PurchaseRequest,
    session: AsyncSession = Depends(get_db),
) -> dict:
    if not payload.courseId and not payload.serviceId:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Specify courseId or serviceId",
        )
    product = f"курс #{payload.courseId}" if payload.courseId else f"услуга #{payload.serviceId}"
    await LeadRepository(session).create(
        contact=payload.contact.strip(),
        message=f"Запрос на покупку: {product}",
        lead_type="purchase",
    )
    settings = get_settings()
    await notify_admin(
        f"🛒 Запрос на покупку: {product}\n"
        f"Контакт: {payload.contact}\n"
        f"Связаться: {settings.support_contact}"
    )
    return {"ok": True, "message": "Запрос отправлен. Менеджер напишет вам в Telegram."}

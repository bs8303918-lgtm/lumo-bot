from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db
from api.schemas import BannerResponse, CourseItem, ExpertServiceItem, SiteMetaResponse
from config import get_settings
from db.repositories.catalog import CatalogRepository

router = APIRouter(tags=["catalog"])


@router.get("/services", response_model=list[ExpertServiceItem])
async def list_services(session: AsyncSession = Depends(get_db)) -> list[dict]:
    return await CatalogRepository(session).list_services()


@router.get("/courses", response_model=list[CourseItem])
async def list_courses(session: AsyncSession = Depends(get_db)) -> list[dict]:
    return await CatalogRepository(session).list_courses()


@router.get("/banner", response_model=BannerResponse)
async def get_banner() -> dict:
    settings = get_settings()
    return {
        "title": "Нужна помощь с подачей?",
        "subtitle": "Наши эксперты помогут упаковать твой кейс",
        "ctaLabel": "Связаться",
        "ctaUrl": settings.community_telegram_url,
    }


@router.get("/meta", response_model=SiteMetaResponse)
async def get_site_meta() -> dict:
    settings = get_settings()
    handle = settings.community_telegram_handle
    return {
        "title": "AI Startify Grants",
        "subtitle": "Витрина возможностей",
        "communityHandle": handle,
        "communityUrl": settings.community_telegram_url,
        "supportContact": settings.support_contact,
    }

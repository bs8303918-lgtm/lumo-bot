import asyncio
import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from analytics.event_types import AI_SEARCH, CATALOG_VIEW, INTEREST_SET
from api.auth import get_current_user
from api.deps import get_db
from bot.handlers.interests import INTEREST_MIN_LENGTH
from config import get_settings
from db.models import User
from db.repositories.channels import ChannelRepository
from db.repositories.opportunity_catalog import (
    OPPORTUNITY_TYPES,
    parse_interest_categories,
)
from db.repositories.users import MatchRepository, MessageRepository, SystemStateRepository, UserRepository
from db.repositories.users import EventRepository
from services.ai_search_limit import ai_search_usage, enforce_ai_search_limit
from services.interest_matcher import (
    entry_all_tags,
    extract_categories_from_text,
    resolve_catalog_filter,
)
from services.opportunity_catalog import catalog_repo
from services.subscription import has_ai_access, public_plans, subscription_status
from services.shared_room_access import effective_catalog_user, read_room_student_id_header
from bot.background import run_interest_side_effects
from services.catalog_display import entry_has_cash_prize, sort_opportunities_by_newest
from services.webapp_catalog import (
    SEARCH_SUGGESTIONS,
    build_category_list,
    category_chips,
    dedupe_opportunities,
    match_opportunities_for_user_async,
    plural_opportunities,
    serialize_opportunity,
    sort_opportunities_by_deadline,
)

router = APIRouter(tags=["lumo"])

ALL_TYPES = [t for t in OPPORTUNITY_TYPES if t != "другое"]


class MatchRequest(BaseModel):
    query: str | None = Field(default=None, max_length=2000)
    limit: int = Field(default=12, ge=1, le=30)
    saveInterest: bool = Field(default=False)


class SetInterestRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)


class MatchFeedbackRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    catalogId: int = Field(ge=1)
    helpful: bool
    categories: list[str] = Field(default_factory=list)


class MatchFeedbackBatchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    helpful: bool
    catalogIds: list[int] = Field(min_length=1, max_length=30)
    categories: list[str] = Field(default_factory=list)


class MentorRequestPayload(BaseModel):
    message: str | None = Field(default=None, max_length=1000)


class AssistantRequest(BaseModel):
    message: str = Field(min_length=3, max_length=2000)


class CreateReviewRequest(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=10, max_length=4000)
    link: str | None = Field(default=None, max_length=512)


class SaveOpportunityRequest(BaseModel):
    catalogId: int = Field(ge=1)
    status: str | None = Field(default=None)


class UpdateSavedOpportunityRequest(BaseModel):
    status: str | None = Field(default=None)
    checklist: list[dict] | None = Field(default=None)
    notifyOptIn: bool | None = Field(default=None)


class StudentProfileRequest(BaseModel):
    grade: str | None = Field(default=None, max_length=32)
    region: str | None = Field(default=None, max_length=64)
    englishLevel: str | None = Field(default=None, max_length=16)
    subjects: list[str] = Field(default_factory=list, max_length=12)
    visibleInCommunity: bool | None = None


async def _persist_interest(
    session: AsyncSession,
    user: User,
    text: str,
    *,
    skip_llm: bool = False,
    reset_llm_queue: bool = True,
) -> list[str]:
    if reset_llm_queue and (user.interest_query or "").strip() != text.strip():
        await MatchRepository(session).clear_processed_for_user(user.id)
        max_raw_id = await MessageRepository(session).get_max_raw_message_id()
        await SystemStateRepository(session).set_llm_min_raw_id(user.id, max_raw_id)
    from services.interest_admin_review import save_user_interest_profile

    profile = await save_user_interest_profile(
        user.id,
        text,
        session=session,
        telegram_id=user.telegram_id,
        username=user.username,
        skip_llm=skip_llm,
    )
    return profile.all_categories()


async def _search_catalog(
    session: AsyncSession,
    user: User,
    query: str,
    *,
    limit: int = 12,
) -> tuple[list[dict], list[str], list[str]]:
    from services.match_feedback_memory import load_match_feedback_hints

    categories = extract_categories_from_text(query)
    search_types, extra_tags = resolve_catalog_filter(categories)
    repo = catalog_repo(session)
    raw, feedback_hints = await asyncio.gather(
        repo.get_active_for_user(
            user.id,
            search_types,
            limit=50,
            extra_tags=extra_tags,
        ),
        load_match_feedback_hints(user.id, query),
    )
    items, matched_categories = await match_opportunities_for_user_async(
        query,
        raw,
        limit=limit,
        feedback_hints=feedback_hints,
        user=user,
    )
    return items, matched_categories, categories


@router.get("/lumo/meta")
async def lumo_meta() -> dict:
    settings = get_settings()
    return {
        "botUsername": settings.telegram_bot_username or "LumoAI1bot",
        "webAppUrl": settings.resolved_webapp_url,
        "supportContact": settings.support_contact,
        "communityTelegramUrl": settings.community_telegram_url.strip(),
        "communityTelegramHandle": settings.community_telegram_handle.strip() or "Lumo Community",
        "interestMinLength": INTEREST_MIN_LENGTH,
        "maxUserChannels": settings.max_user_channels,
        "aiSearchDailyLimit": settings.ai_search_daily_limit,
        "searchSuggestions": SEARCH_SUGGESTIONS,
        "subscriptionsEnforced": settings.subscriptions_enforced,
        "subscriptionPreviewEnabled": settings.subscription_preview_enabled,
        "startifyCheckoutUrl": settings.startify_checkout_url.strip() or None,
        "kaspiPaymentPhone": settings.kaspi_payment_phone.strip() or "+7 775 499 8313",
        "plans": public_plans(),
    }


@router.get("/lumo/subscription-plans")
async def lumo_subscription_plans() -> dict:
    return {"plans": public_plans(), "freemiumAiLimit": get_settings().ai_search_daily_limit}


@router.get("/users/me")
async def get_me(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    settings = get_settings()
    from services.student_profile import serialize_student_profile

    categories = parse_interest_categories(user.interest_categories_json)
    is_admin = settings.user_is_admin(user.telegram_id, user.email)
    search = await ai_search_usage(session, user.id, telegram_id=user.telegram_id, user=user)
    catalog_count = await catalog_repo(session).count_active_for_user(user.id)
    return {
        "profile": serialize_student_profile(user),
        "telegramId": user.telegram_id,
        "username": user.username,
        "interestQuery": user.interest_query,
        "categories": categories,
        "hasInterest": bool(user.interest_query and user.interest_query.strip()),
        "isAdmin": is_admin,
        "aiSearchUsed": search["used"],
        "aiSearchLimit": search["limit"],
        "aiSearchRemaining": search["remaining"],
        "hasAiAccess": has_ai_access(user, telegram_id=user.telegram_id),
        "catalogCount": catalog_count,
        "subscription": subscription_status(user),
        "role": (user.role or "student").lower(),
    }


@router.get("/users/profile")
async def get_student_profile(
    user: User = Depends(get_current_user),
) -> dict:
    from services.student_profile import serialize_student_profile

    return serialize_student_profile(user)


@router.put("/users/profile")
async def set_student_profile(
    payload: StudentProfileRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    from services.student_profile import (
        normalize_english_level,
        serialize_student_profile,
        subjects_to_json,
    )

    if payload.grade is not None:
        user.grade = payload.grade.strip() or None
    if payload.region is not None:
        user.region = payload.region.strip() or None
    if payload.englishLevel is not None:
        normalized = normalize_english_level(payload.englishLevel)
        if payload.englishLevel.strip() and normalized is None:
            raise HTTPException(status_code=422, detail="Некорректный уровень английского")
        user.english_level = normalized
    if payload.subjects:
        user.subjects_json = subjects_to_json(payload.subjects)
    elif payload.subjects == []:
        user.subjects_json = subjects_to_json([])
    if payload.visibleInCommunity is not None:
        user.visible_in_community = payload.visibleInCommunity

    await session.commit()
    return serialize_student_profile(user)


@router.get("/users/channels")
async def list_my_channels(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[dict]:
    channels = await ChannelRepository(session).get_user_channels(user.id)
    return [
        {
            "id": ch.id,
            "title": ch.channel_title or ch.channel_identifier,
            "identifier": ch.channel_identifier,
        }
        for ch in channels
    ]


@router.delete("/users/channels/{channel_id}")
async def delete_my_channel(
    channel_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    channel_repo = ChannelRepository(session)
    removed = await channel_repo.remove_user_channel(user.id, channel_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Channel not found")

    await EventRepository(session).log(
        "channel_removed",
        user_id=user.id,
        metadata={"channel": removed, "source": "mini_app"},
    )
    await session.commit()
    return {"ok": True, "identifier": removed}


@router.post("/users/interest")
async def set_interest(
    payload: SetInterestRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    text = payload.query.strip()
    if len(text) < INTEREST_MIN_LENGTH:
        raise HTTPException(
            status_code=422,
            detail=f"Минимум {INTEREST_MIN_LENGTH} символов — опиши подробнее",
        )

    await enforce_ai_search_limit(session, user.id, telegram_id=user.telegram_id)

    interest_changed = (user.interest_query or "").strip() != text
    items, _matched, categories = await _search_catalog(session, user, text, limit=12)

    if not interest_changed and not categories:
        categories = (
            parse_interest_categories(user.interest_categories_json)
            or extract_categories_from_text(text)
        )

    count = len(items)
    if count:
        message = f"Подобрал {count} {plural_opportunities(count)} под твой запрос."
    else:
        message = (
            "По твоему запросу пока ничего не нашёл — профиль сохраняю, "
            "пришлю в бот, когда появится подходящее."
        )

    background_tasks.add_task(
        run_interest_side_effects,
        user.id,
        text,
        results_count=count,
        profile_changed=interest_changed,
        log_ai_search=True,
    )

    return {
        "ok": True,
        "categories": category_chips(categories),
        "message": message,
        "items": items,
        "noMatch": count == 0,
        "suggestions": SEARCH_SUGGESTIONS if count == 0 else [],
        "cardsSentToBot": 0,
    }


@router.get("/lumo/categories")
async def lumo_categories(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    room_student_id: int | None = Depends(read_room_student_id_header),
) -> list[dict]:
    from services.early_access import early_access_cutoff

    catalog_user = await effective_catalog_user(session, user, room_student_id)
    cutoff = early_access_cutoff(catalog_user)
    counts = await catalog_repo(session).count_active_by_type_for_user(catalog_user.id, visible_before=cutoff)
    total = await catalog_repo(session).count_active_for_user(catalog_user.id, visible_before=cutoff)
    return build_category_list(counts, total_entries=total)


@router.get("/lumo/catalog-bootstrap")
async def lumo_catalog_bootstrap(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=50),
    room_student_id: int | None = Depends(read_room_student_id_header),
) -> dict:
    """Categories + first catalog page in one request (faster Mini App load)."""
    from db.base import async_session_factory
    from services.early_access import early_access_cutoff

    catalog_user = await effective_catalog_user(session, user, room_student_id)
    cutoff = early_access_cutoff(catalog_user)
    fetch_cap = min(120, limit * 6 + 24)
    user_id = catalog_user.id

    async def load_counts() -> tuple[dict[str, int], int]:
        async with async_session_factory() as s:
            repo = catalog_repo(s)
            counts = await repo.count_active_by_type_for_user(user_id, visible_before=cutoff)
            total = await repo.count_active_for_user(user_id, visible_before=cutoff)
            return counts, total

    async def load_page() -> list:
        async with async_session_factory() as s:
            return await catalog_repo(s).list_all_active_for_user(
                user_id, ALL_TYPES, max_rows=fetch_cap, visible_before=cutoff
            )

    (counts, total), fresh = await asyncio.gather(load_counts(), load_page())
    unique = dedupe_opportunities(fresh)
    categories = build_category_list(counts, total_entries=total)
    sorted_items = sort_opportunities_by_deadline(unique)
    page = sorted_items[:limit]
    return {
        "categories": categories,
        "items": [serialize_opportunity(e, user=catalog_user) for e in page],
        "total": total,
        "offset": 0,
        "limit": limit,
        "hasMore": total > limit,
    }


def _deadline_within_days(entry, max_days: int) -> bool:
    from datetime import date

    from llm.deadline import parse_deadline
    from services.catalog_freshness import message_posted_at

    posted = message_posted_at(entry)
    anchor = posted.date() if posted else None
    parsed = parse_deadline(entry.deadline, anchor_date=anchor)
    if parsed is None:
        return False
    days_left = (parsed - date.today()).days
    return 0 <= days_left <= max_days


@router.get("/lumo/opportunities")
async def lumo_opportunities(
    category: str | None = Query(default=None),
    types: str | None = Query(default=None, description="Comma-separated opportunity types"),
    q: str | None = Query(default=None),
    sort: str = Query(default="deadline", pattern="^(newest|deadline|relevance)$"),
    cash_prize: str = Query(default="any", pattern="^(any|yes|no)$"),
    deadline_within_days: int | None = Query(default=None, ge=1, le=365),
    fmt: str = Query(default="any", pattern="^(any|online|offline)$", alias="format"),
    team: str = Query(default="any", pattern="^(any|team|solo)$"),
    limit: int = Query(default=20, ge=1, le=50),
    page_size: int | None = Query(default=None, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    room_student_id: int | None = Depends(read_room_student_id_header),
) -> dict:
    from services.early_access import early_access_cutoff
    from services.match_score import raw_match_score
    from services.opportunity_traits import matches_format_filter, matches_team_filter

    catalog_user = await effective_catalog_user(session, user, room_student_id)
    cutoff = early_access_cutoff(catalog_user)
    repo = catalog_repo(session)
    page_limit = page_size or limit

    if types:
        selected = [t.strip().lower() for t in types.split(",") if t.strip()]
        types_filter = [t for t in selected if t in ALL_TYPES]
        if not types_filter:
            types_filter = ALL_TYPES
    elif category and category != "all":
        types_filter = [category]
    else:
        types_filter = ALL_TYPES

    fetch_cap = min(max(page_limit + offset + page_limit, 60), 200)
    items = await repo.get_active_for_user(
        catalog_user.id, types_filter, limit=fetch_cap, visible_before=cutoff
    )
    unique = dedupe_opportunities(items)

    if q:
        needle = q.strip().lower()
        unique = [
            e
            for e in unique
            if needle in (e.title or "").lower()
            or needle in (e.description or "").lower()
            or needle in (e.source_channel_name or "").lower()
            or any(needle in tag for tag in entry_all_tags(e))
        ]

    if cash_prize == "yes":
        unique = [e for e in unique if entry_has_cash_prize(e)]
    elif cash_prize == "no":
        unique = [e for e in unique if not entry_has_cash_prize(e)]

    if deadline_within_days:
        unique = [e for e in unique if _deadline_within_days(e, deadline_within_days)]

    if fmt != "any":
        unique = [e for e in unique if matches_format_filter(e, fmt)]

    if team != "any":
        unique = [e for e in unique if matches_team_filter(e, team)]

    if sort == "newest":
        sorted_items = sort_opportunities_by_newest(unique)
    elif sort == "relevance":
        sorted_items = sorted(unique, key=lambda e: raw_match_score(catalog_user, e), reverse=True)
    else:
        sorted_items = sort_opportunities_by_deadline(unique)

    total = len(sorted_items)
    page = sorted_items[offset : offset + page_limit]
    return {
        "items": [serialize_opportunity(e, user=catalog_user) for e in page],
        "total": total,
        "offset": offset,
        "limit": page_limit,
        "hasMore": offset + page_limit < total,
        "sort": sort,
    }


@router.get("/lumo/opportunities/{item_id}")
async def lumo_opportunity(
    item_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    room_student_id: int | None = Depends(read_room_student_id_header),
) -> dict:
    catalog_user = await effective_catalog_user(session, user, room_student_id)
    repo = catalog_repo(session)
    row = await repo.get_entry_with_channel(item_id)
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    entry, channel = row
    if not entry.is_active:
        raise HTTPException(status_code=404, detail="Not found")

    if not await repo.user_can_access_entry(catalog_user.id, entry.id):
        raise HTTPException(status_code=403, detail="Not available for your channels")

    await EventRepository(session).log(CATALOG_VIEW, user_id=user.id, related_id=entry.id)
    await session.commit()

    raw_message = getattr(entry, "raw_message", None)
    message_id = raw_message.telegram_message_id if raw_message else None
    from services.opportunity_ai_brief import get_or_build_brief
    from services.webapp_catalog import serialize_opportunity_detail

    payload = serialize_opportunity_detail(
        entry,
        channel_identifier=channel.channel_identifier,
        telegram_message_id=message_id,
        user=catalog_user,
    )
    payload["brief"] = await get_or_build_brief(session, entry)
    return payload


@router.get("/lumo/opportunities/{item_id}/similar")
async def lumo_similar_opportunities(
    item_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    room_student_id: int | None = Depends(read_room_student_id_header),
    limit: int = Query(default=6, ge=1, le=12),
) -> dict:
    from services.early_access import early_access_cutoff
    from services.similar_opportunities import find_similar

    catalog_user = await effective_catalog_user(session, user, room_student_id)
    cutoff = early_access_cutoff(catalog_user)
    repo = catalog_repo(session)
    row = await repo.get_entry_with_channel(item_id)
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    entry, _channel = row

    pool = await repo.get_active_for_user(
        catalog_user.id, [entry.opportunity_type], limit=80, visible_before=cutoff
    )
    if len(pool) < limit + 1:
        pool = pool + await repo.get_active_for_user(
            catalog_user.id, ALL_TYPES, limit=120, visible_before=cutoff
        )
    pool = dedupe_opportunities(pool)

    similar = find_similar(entry, pool, limit=limit)
    return {"items": [serialize_opportunity(e, user=catalog_user) for e in similar]}


@router.get("/lumo/opportunities/{item_id}/peers")
async def lumo_opportunity_peers(
    item_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    room_student_id: int | None = Depends(read_room_student_id_header),
) -> dict:
    """«Кто ещё подаётся» — только opt-in счётчик, без раскрытия личностей."""
    from db.repositories.saved_opportunities import SavedOpportunityRepository

    catalog_user = await effective_catalog_user(session, user, room_student_id)
    total, same_region = await SavedOpportunityRepository(session).count_opted_in_peers(
        item_id,
        exclude_user_id=catalog_user.id,
        region=catalog_user.region,
    )
    return {
        "count": total,
        "sameRegionCount": same_region,
        "visibleToOthers": bool(catalog_user.visible_in_community),
    }


@router.post("/lumo/opportunities/{item_id}/assistant")
async def lumo_opportunity_assistant(
    item_id: int,
    payload: AssistantRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    room_student_id: int | None = Depends(read_room_student_id_header),
) -> dict:
    """Premium: AI-ассистент помогает собрать документы/эссе под конкретный конкурс."""
    from services.subscription import is_paid_plan_active

    catalog_user = await effective_catalog_user(session, user, room_student_id)
    settings = get_settings()
    is_admin = settings.user_is_admin(catalog_user.telegram_id, catalog_user.email)
    if not is_admin and not is_paid_plan_active(catalog_user):
        raise HTTPException(
            status_code=402,
            detail="AI-ассистент по подаче доступен на платных тарифах",
        )
    if not settings.llm_configured:
        raise HTTPException(status_code=503, detail="AI-ассистент временно недоступен")

    repo = catalog_repo(session)
    row = await repo.get_entry_with_channel(item_id)
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    entry, _channel = row

    from llm.client import LLMClient

    data, _raw = await LLMClient().draft_application_help(
        title=entry.title,
        opp_type=entry.opportunity_type,
        description=entry.description,
        requirements=entry.requirements,
        deadline=entry.deadline,
        student_message=payload.message.strip(),
    )
    advice = (data or {}).get("advice") if data else None
    if not advice:
        raise HTTPException(status_code=502, detail="Не удалось получить ответ от AI, попробуй ещё раз")

    await EventRepository(session).log(
        "ai_assistant_used",
        user_id=catalog_user.id,
        related_id=entry.id,
    )
    await session.commit()
    return {"advice": advice}


_MENTOR_ADDON_PLANS = {"plan_6m", "plan_12m", "unlimited"}


@router.post("/lumo/opportunities/{item_id}/request-mentor")
async def lumo_request_mentor(
    item_id: int,
    payload: MentorRequestPayload,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    room_student_id: int | None = Depends(read_room_student_id_header),
) -> dict:
    """Mentor add-on: студент запрашивает подбор ментора под конкретный конкурс (Premium 6m+)."""
    from db.repositories.mentor_requests import MentorRequestRepository
    from services.subscription import is_paid_plan_active

    catalog_user = await effective_catalog_user(session, user, room_student_id)
    settings = get_settings()
    is_admin = settings.user_is_admin(catalog_user.telegram_id, catalog_user.email)
    plan = (catalog_user.tariff_plan or "freemium").lower()
    if not is_admin and not (is_paid_plan_active(catalog_user) and plan in _MENTOR_ADDON_PLANS):
        raise HTTPException(
            status_code=402,
            detail="Подбор ментора доступен на тарифах от 6 месяцев",
        )

    repo = catalog_repo(session)
    row = await repo.get_entry_with_channel(item_id)
    if not row:
        raise HTTPException(status_code=404, detail="Not found")

    mentor_repo = MentorRequestRepository(session)
    existing = await mentor_repo.get_existing(catalog_user.id, item_id)
    if existing:
        return {"ok": True, "status": existing.status, "alreadyRequested": True}

    request = await mentor_repo.create(
        student_user_id=catalog_user.id,
        catalog_id=item_id,
        message=(payload.message or "").strip() or None,
    )
    await session.commit()
    return {"ok": True, "status": request.status, "alreadyRequested": False}


@router.get("/lumo/reviews")
async def lumo_reviews_feed(
    session: AsyncSession = Depends(get_db),
    limit: int = Query(default=30, ge=1, le=100),
) -> dict:
    from db.repositories.opportunity_reviews import OpportunityReviewRepository, serialize_review

    reviews = await OpportunityReviewRepository(session).list_recent(limit=limit)
    return {"items": [serialize_review(r, include_catalog=True) for r in reviews]}


@router.get("/lumo/opportunities/{item_id}/reviews")
async def lumo_opportunity_reviews(
    item_id: int,
    session: AsyncSession = Depends(get_db),
    limit: int = Query(default=30, ge=1, le=100),
) -> dict:
    from db.repositories.opportunity_reviews import OpportunityReviewRepository, serialize_review

    reviews = await OpportunityReviewRepository(session).list_for_catalog(item_id, limit=limit)
    return {"items": [serialize_review(r) for r in reviews]}


@router.post("/lumo/opportunities/{item_id}/reviews")
async def lumo_create_review(
    item_id: int,
    payload: CreateReviewRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    from db.repositories.opportunity_reviews import OpportunityReviewRepository, serialize_review

    repo = catalog_repo(session)
    entry = await repo.get_entry_with_channel(item_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Not found")

    author = user.display_name or user.username or "Аноним"
    review = await OpportunityReviewRepository(session).create(
        catalog_id=item_id,
        user_id=user.id,
        title=payload.title.strip(),
        body=payload.body.strip(),
        link=(payload.link or "").strip() or None,
        author_display_name=author,
    )
    await session.commit()
    return serialize_review(review)


@router.post("/lumo/match")
async def lumo_match(
    payload: MatchRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    room_student_id: int | None = Depends(read_room_student_id_header),
) -> dict:
    catalog_user = await effective_catalog_user(session, user, room_student_id)
    query = (payload.query or catalog_user.interest_query or "").strip()
    if len(query) < 3:
        raise HTTPException(status_code=422, detail="Опиши запрос подробнее")

    await enforce_ai_search_limit(
        session,
        catalog_user.id,
        telegram_id=catalog_user.telegram_id,
    )

    save_profile = payload.saveInterest and len(query) >= INTEREST_MIN_LENGTH
    if save_profile:
        await _persist_interest(session, catalog_user, query, skip_llm=False)

    items, cat_list, _raw_categories = await _search_catalog(
        session,
        catalog_user,
        query,
        limit=payload.limit,
    )

    count = len(items)
    if count:
        message = f"Подобрал {count} {plural_opportunities(count)} под твой запрос."
    elif save_profile:
        message = (
            "По твоему запросу пока ничего не нашёл — профиль сохраняю, "
            "пришлю в бот, когда появится подходящее."
        )
    else:
        message = "По этому запросу пока ничего не нашёл."

    background_tasks.add_task(
        run_interest_side_effects,
        catalog_user.id,
        query,
        results_count=count,
        profile_changed=False,
        log_ai_search=True,
    )

    return {
        "query": query,
        "categories": category_chips(cat_list),
        "message": message,
        "items": items,
        "noMatch": count == 0,
        "suggestions": SEARCH_SUGGESTIONS if count == 0 else [],
    }


async def _persist_match_feedback(
    user_id: int,
    query: str,
    catalog_id: int,
    helpful: bool,
    categories: list[str],
) -> None:
    from services.match_feedback_memory import invalidate_feedback_cache
    from services.training_collector import record_search_feedback

    await record_search_feedback(
        user_id=user_id,
        interest_query=query,
        catalog_id=catalog_id,
        helpful=helpful,
        categories=categories,
    )
    invalidate_feedback_cache(user_id)


@router.post("/lumo/match-feedback")
async def lumo_match_feedback(
    payload: MatchFeedbackRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
) -> dict:
    """👍/👎 по одной карточке — в training_samples task=match."""
    from services.match_feedback_memory import record_optimistic_feedback

    record_optimistic_feedback(
        user.id,
        payload.catalogId,
        payload.helpful,
        payload.query.strip(),
    )
    background_tasks.add_task(
        _persist_match_feedback,
        user.id,
        payload.query.strip(),
        payload.catalogId,
        payload.helpful,
        payload.categories,
    )
    return {"ok": True}


@router.post("/lumo/match-feedback/batch")
async def lumo_match_feedback_batch(
    payload: MatchFeedbackBatchRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
) -> dict:
    """Оценка всей выдачи сразу — каждая карточка в training."""
    from services.match_feedback_memory import record_optimistic_feedback

    query = payload.query.strip()
    for catalog_id in payload.catalogIds:
        record_optimistic_feedback(user.id, catalog_id, payload.helpful, query)
        background_tasks.add_task(
            _persist_match_feedback,
            user.id,
            query,
            catalog_id,
            payload.helpful,
            payload.categories,
        )
    return {"ok": True, "count": len(payload.catalogIds)}


def _serialize_saved(row, *, user: User) -> dict:
    import json

    checklist = []
    if row.checklist_json:
        try:
            data = json.loads(row.checklist_json)
            if isinstance(data, list):
                checklist = data
        except (json.JSONDecodeError, TypeError):
            checklist = []
    payload = serialize_opportunity(row.catalog, user=user) if row.catalog else {"id": row.catalog_id}
    payload["savedStatus"] = row.status
    payload["checklist"] = checklist
    payload["notifyOptIn"] = row.notify_opt_in
    payload["savedAt"] = row.created_at.isoformat() if row.created_at else None
    return payload


@router.get("/lumo/saved")
async def list_saved_opportunities(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    from db.repositories.saved_opportunities import SavedOpportunityRepository

    rows = await SavedOpportunityRepository(session).list_for_user(user.id)
    return {"items": [_serialize_saved(row, user=user) for row in rows]}


@router.post("/lumo/saved")
async def save_opportunity(
    payload: SaveOpportunityRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    from db.repositories.saved_opportunities import SAVED_STATUSES, SavedOpportunityRepository

    if payload.status and payload.status not in SAVED_STATUSES:
        raise HTTPException(status_code=422, detail=f"status должен быть одним из {SAVED_STATUSES}")

    repo = catalog_repo(session)
    entry = await repo.get_entry_with_channel(payload.catalogId)
    if not entry:
        raise HTTPException(status_code=404, detail="Not found")

    row = await SavedOpportunityRepository(session).upsert(user.id, payload.catalogId, status=payload.status)
    await session.commit()
    await session.refresh(row, attribute_names=["catalog"])
    return _serialize_saved(row, user=user)


@router.patch("/lumo/saved/{catalog_id}")
async def update_saved_opportunity(
    catalog_id: int,
    payload: UpdateSavedOpportunityRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    import json

    from db.repositories.saved_opportunities import SAVED_STATUSES, SavedOpportunityRepository

    repo = SavedOpportunityRepository(session)
    row = await repo.get(user.id, catalog_id)
    if not row:
        raise HTTPException(status_code=404, detail="Not saved")

    if payload.status is not None:
        if payload.status not in SAVED_STATUSES:
            raise HTTPException(status_code=422, detail=f"status должен быть одним из {SAVED_STATUSES}")
        row.status = payload.status
    if payload.checklist is not None:
        row.checklist_json = json.dumps(payload.checklist, ensure_ascii=False)
    if payload.notifyOptIn is not None:
        row.notify_opt_in = payload.notifyOptIn

    await session.commit()
    await session.refresh(row, attribute_names=["catalog"])
    return _serialize_saved(row, user=user)


@router.delete("/lumo/saved/{catalog_id}")
async def delete_saved_opportunity(
    catalog_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    from db.repositories.saved_opportunities import SavedOpportunityRepository

    removed = await SavedOpportunityRepository(session).remove(user.id, catalog_id)
    await session.commit()
    if not removed:
        raise HTTPException(status_code=404, detail="Not saved")
    return {"ok": True}

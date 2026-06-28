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
from services.subscription import public_plans, subscription_status
from bot.background import run_interest_side_effects
from services.webapp_catalog import (
    SEARCH_SUGGESTIONS,
    build_category_list,
    category_chips,
    dedupe_opportunities,
    match_opportunities_for_user,
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
    categories = extract_categories_from_text(query)
    search_types, extra_tags = resolve_catalog_filter(categories)
    repo = catalog_repo(session)
    raw = await repo.get_active_for_user(
        user.id,
        search_types,
        limit=80,
        extra_tags=extra_tags,
    )
    items, matched_categories = match_opportunities_for_user(query, raw, limit=limit)
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
    categories = parse_interest_categories(user.interest_categories_json)
    is_admin = settings.is_admin(user.telegram_id)
    search = await ai_search_usage(session, user.id, telegram_id=user.telegram_id, user=user)
    catalog_count = await catalog_repo(session).count_active_for_user(user.id)
    return {
        "telegramId": user.telegram_id,
        "username": user.username,
        "interestQuery": user.interest_query,
        "categories": categories,
        "hasInterest": bool(user.interest_query and user.interest_query.strip()),
        "isAdmin": is_admin,
        "aiSearchUsed": search["used"],
        "aiSearchLimit": search["limit"],
        "aiSearchRemaining": search["remaining"],
        "catalogCount": catalog_count,
        "subscription": subscription_status(user),
    }


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
) -> list[dict]:
    counts = await catalog_repo(session).count_active_by_type_for_user(user.id)
    total = await catalog_repo(session).count_active_for_user(user.id)
    return build_category_list(counts, total_entries=total)


@router.get("/lumo/catalog-bootstrap")
async def lumo_catalog_bootstrap(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=50),
) -> dict:
    """Categories + first catalog page in one request (faster Mini App load)."""
    repo = catalog_repo(session)
    fresh = await repo.list_all_active_for_user(user.id, ALL_TYPES, max_rows=500)
    counts: dict[str, int] = {}
    for entry in fresh:
        for tag in entry_all_tags(entry):
            if tag != "другое":
                counts[tag] = counts.get(tag, 0) + 1
    unique = dedupe_opportunities(fresh)
    total = len(unique)
    categories = build_category_list(counts, total_entries=total)
    sorted_items = sort_opportunities_by_deadline(unique)
    page = sorted_items[:limit]
    return {
        "categories": categories,
        "items": [serialize_opportunity(e) for e in page],
        "total": total,
        "offset": 0,
        "limit": limit,
        "hasMore": total > limit,
    }


@router.get("/lumo/opportunities")
async def lumo_opportunities(
    category: str | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    repo = catalog_repo(session)
    types = ALL_TYPES if not category or category == "all" else [category]
    fetch_cap = min(max(limit + offset + limit, 60), 300)
    items = await repo.get_active_for_user(user.id, types, limit=fetch_cap)
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

    sorted_items = sort_opportunities_by_deadline(unique)
    total = len(sorted_items)
    page = sorted_items[offset : offset + limit]
    return {
        "items": [serialize_opportunity(e) for e in page],
        "total": total,
        "offset": offset,
        "limit": limit,
        "hasMore": offset + limit < total,
    }


@router.get("/lumo/opportunities/{item_id}")
async def lumo_opportunity(
    item_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    repo = catalog_repo(session)
    row = await repo.get_entry_with_channel(item_id)
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    entry, _channel = row
    if not entry.is_active:
        raise HTTPException(status_code=404, detail="Not found")

    if not await repo.user_can_access_entry(user.id, entry.id):
        raise HTTPException(status_code=403, detail="Not available for your channels")

    await EventRepository(session).log(CATALOG_VIEW, user_id=user.id, related_id=entry.id)
    await session.commit()

    return serialize_opportunity(entry)


@router.post("/lumo/match")
async def lumo_match(
    payload: MatchRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    query = (payload.query or user.interest_query or "").strip()
    if len(query) < 3:
        raise HTTPException(status_code=422, detail="Опиши запрос подробнее")

    save_profile = payload.saveInterest and len(query) >= INTEREST_MIN_LENGTH
    if save_profile:
        await enforce_ai_search_limit(session, user.id, telegram_id=user.telegram_id)

    items, cat_list, _raw_categories = await _search_catalog(
        session,
        user,
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

    if save_profile:
        background_tasks.add_task(
            run_interest_side_effects,
            user.id,
            query,
            results_count=count,
            profile_changed=(user.interest_query or "").strip() != query,
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

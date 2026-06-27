"""Промо-рассылки с трекингом кликов."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import asyncio

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.exc import OperationalError

from analytics.event_types import (
    CAMPAIGN_APPLY_CLICK,
    CAMPAIGN_LINK_CLICK,
    CAMPAIGN_SENT,
    CAMPAIGN_TELEGRAM_CLICK,
)
from bot.instance import get_notify_bot
from config import BASE_DIR
from db.base import async_session_factory
from db.models import Event, PromoCampaignDelivery, User
from db.repositories.users import EventRepository, UserRepository
from services.notification_service import is_unreachable_user_error

logger = logging.getLogger(__name__)

CAMPAIGNS_DIR = BASE_DIR / "data" / "campaigns"


@dataclass(frozen=True)
class PromoCampaign:
    slug: str
    title: str
    learn: str
    format: str
    location: str
    deadline: str
    promo_code: str
    promo_discount: str
    apply_url: str
    telegram_url: str
    info_url: str
    tiers: dict[str, list[int]]

    def all_user_ids(self) -> list[tuple[int, str]]:
        rows: list[tuple[int, str]] = []
        for tier, ids in self.tiers.items():
            for user_id in ids:
                rows.append((user_id, tier))
        return rows


def load_campaign(slug: str) -> PromoCampaign:
    path = CAMPAIGNS_DIR / f"{slug}.json"
    if not path.exists():
        raise FileNotFoundError(f"Campaign not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return PromoCampaign(
        slug=data["slug"],
        title=data["title"],
        learn=data["learn"],
        format=data["format"],
        location=data["location"],
        deadline=data["deadline"],
        promo_code=data["promo_code"],
        promo_discount=data.get("promo_discount", "15%"),
        apply_url=data["apply_url"],
        telegram_url=data.get("telegram_url") or data.get("info_url", ""),
        info_url=data.get("info_url") or data.get("telegram_url", ""),
        tiers=data["tiers"],
    )


def _tier_header(tier: str) -> str:
    if tier == "perfect":
        return (
            "🎯 Нашли <b>100% совпадение</b> под твои интересы!\n\n"
            "Бот подобрал для тебя идеальную программу для прокачки "
            "предпринимательских навыков и запуска твоего проекта."
        )
    if tier == "high":
        return (
            "⚡ <b>Высокое соответствие</b> под твой профиль!\n\n"
            "Нашли программу, которая отлично ложится на твои интересы — "
            "хакатоны, проекты и стартапы."
        )
    return (
        "🔍 Программа, которая <b>может зайти</b> под твои интересы\n\n"
        "Если развиваешь проект или хочешь упаковать идею в продукт — "
        "посмотри этот лагерь."
    )


def format_campaign_message(campaign: PromoCampaign, *, tier: str) -> str:
    header = _tier_header(tier)
    return (
        f"{header}\n\n"
        f"<b>Что:</b> {campaign.title}\n"
        f"<b>Чему научишься:</b> {campaign.learn}\n"
        f"<b>Формат:</b> {campaign.format}\n"
        f"<b>Где:</b> {campaign.location}\n"
        f"<b>Дедлайн (старт):</b> {campaign.deadline}\n\n"
        f"🔥 Эксклюзивный бонус от нас — скидка {campaign.promo_discount} "
        f"по промокоду: <code>{campaign.promo_code}</code>\n\n"
        f"📝 <a href=\"{campaign.apply_url}\">Подать заявку</a>\n"
        f"📱 <a href=\"{campaign.telegram_url or campaign.info_url}\">Пост в Telegram</a>"
    )


def campaign_keyboard(slug: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👉 Подать заявку",
                    callback_data=f"camp:{slug}:apply",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📱 Пост в Telegram",
                    callback_data=f"camp:{slug}:telegram",
                ),
            ],
        ]
    )


async def send_campaign_to_user(
    campaign: PromoCampaign,
    user: User,
    *,
    tier: str,
    force: bool = False,
) -> str:
    """Returns: sent | skipped | unreachable | error"""
    async with async_session_factory() as session:
        if not force:
            existing = await session.get(
                PromoCampaignDelivery,
                {"campaign_slug": campaign.slug, "user_id": user.id},
            )
            if existing:
                return "skipped"

    bot = get_notify_bot()
    text = format_campaign_message(campaign, tier=tier)
    try:
        await bot.send_message(
            user.telegram_id,
            text,
            parse_mode="HTML",
            reply_markup=campaign_keyboard(campaign.slug),
            disable_web_page_preview=False,
        )
    except Exception as exc:
        if is_unreachable_user_error(exc):
            return "unreachable"
        logger.warning("campaign send failed user=%s: %s", user.id, exc)
        return "error"

    async with async_session_factory() as session:
        event_repo = EventRepository(session)
        for attempt in range(5):
            try:
                session.add(
                    PromoCampaignDelivery(
                        campaign_slug=campaign.slug,
                        user_id=user.id,
                        tier=tier,
                    )
                )
                await event_repo.log(
                    CAMPAIGN_SENT,
                    user_id=user.id,
                    metadata={"campaign": campaign.slug, "tier": tier},
                )
                await session.commit()
                break
            except OperationalError as exc:
                await session.rollback()
                if "locked" not in str(exc).lower() or attempt >= 4:
                    raise
                await asyncio.sleep(0.4 * (attempt + 1))
    return "sent"


async def run_campaign(slug: str, *, force: bool = False) -> dict[str, int]:
    campaign = load_campaign(slug)
    stats = {"sent": 0, "skipped": 0, "unreachable": 0, "missing": 0, "error": 0}

    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        users_by_id: dict[int, User] = {}
        for user_id, _tier in campaign.all_user_ids():
            user = await user_repo.get_by_id(user_id)
            if user:
                users_by_id[user_id] = user
            else:
                stats["missing"] += 1

    for user_id, tier in campaign.all_user_ids():
        user = users_by_id.get(user_id)
        if not user:
            continue
        result = await send_campaign_to_user(campaign, user, tier=tier, force=force)
        stats[result] = stats.get(result, 0) + 1
        await asyncio.sleep(0.05)

    return stats


async def get_campaign_stats(slug: str) -> dict:
    async with async_session_factory() as session:
        from sqlalchemy import func, select

        sent_result = await session.execute(
            select(func.count())
            .select_from(PromoCampaignDelivery)
            .where(PromoCampaignDelivery.campaign_slug == slug)
        )
        sent = int(sent_result.scalar_one())

        events_result = await session.execute(
            select(Event, User.username, User.telegram_id)
            .outerjoin(User, Event.user_id == User.id)
            .where(
                Event.event_type.in_(
                    (
                        CAMPAIGN_SENT,
                        CAMPAIGN_TELEGRAM_CLICK,
                        CAMPAIGN_LINK_CLICK,
                        CAMPAIGN_APPLY_CLICK,
                    )
                )
            )
        )
        rows = list(events_result.all())

    telegram_users: set[int] = set()
    apply_users: set[int] = set()
    telegram_clicks = 0
    apply_clicks = 0
    apply_list: list[str] = []
    telegram_list: list[str] = []

    for event, username, telegram_id in rows:
        meta = {}
        if event.metadata_json:
            try:
                meta = json.loads(event.metadata_json)
            except json.JSONDecodeError:
                pass
        if meta.get("campaign") != slug:
            continue
        ref = f"@{username}" if username else f"tg:{telegram_id}"
        if event.event_type in (CAMPAIGN_TELEGRAM_CLICK, CAMPAIGN_LINK_CLICK):
            telegram_clicks += 1
            if event.user_id:
                telegram_users.add(event.user_id)
                if ref not in telegram_list:
                    telegram_list.append(ref)
        elif event.event_type == CAMPAIGN_APPLY_CLICK:
            apply_clicks += 1
            if event.user_id:
                apply_users.add(event.user_id)
                if ref not in apply_list:
                    apply_list.append(ref)

    return {
        "slug": slug,
        "sent": sent,
        "telegram_clicks": telegram_clicks,
        "apply_clicks": apply_clicks,
        "unique_telegram": len(telegram_users),
        "unique_apply": len(apply_users),
        "ctr_telegram": round(len(telegram_users) / sent * 100, 1) if sent else 0,
        "ctr_apply": round(len(apply_users) / sent * 100, 1) if sent else 0,
        "apply_list": apply_list[:30],
        "telegram_list": telegram_list[:30],
    }


def format_campaign_stats_report(data: dict) -> str:
    lines = [
        f"📣 Кампания: <code>{data['slug']}</code>",
        "",
        f"📤 Отправлено: {data['sent']}",
        f"📱 Telegram: {data['telegram_clicks']} ({data['unique_telegram']} уник.) — CTR {data['ctr_telegram']}%",
        f"📝 Форма заявки: {data['apply_clicks']} ({data['unique_apply']} уник.) — CTR {data['ctr_apply']}%",
    ]
    if data.get("apply_list"):
        lines.extend(["", "📝 Открыли форму:", *([f"  • {u}" for u in data["apply_list"]])])
    if data.get("telegram_list"):
        lines.extend(["", "📱 Открыли Telegram:", *([f"  • {u}" for u in data["telegram_list"]])])
    return "\n".join(lines)

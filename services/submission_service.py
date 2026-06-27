"""User-submitted opportunities — moderation queue and catalog publish."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import CatalogOpportunity, MonitoredChannel, OpportunitySubmission, RawMessage, User
from db.repositories.opportunity_catalog import OPPORTUNITY_TYPES, OpportunityCatalogRepository
from db.repositories.submissions import SubmissionRepository

COMMUNITY_CHANNEL_IDENTIFIER = "lumo_community"
COMMUNITY_CHANNEL_TITLE = "Lumo Community"


def _format_deadline(raw: str | None) -> str:
    if not raw or not raw.strip():
        return "не указан"
    text = raw.strip()
    if len(text) == 10 and text[4] == "-" and text[7] == "-":
        try:
            dt = datetime.strptime(text, "%Y-%m-%d")
            return dt.strftime("%d.%m.%Y")
        except ValueError:
            pass
    return text


def _build_description(submission: OpportunitySubmission) -> str:
    parts: list[str] = []
    if submission.description and submission.description.strip():
        parts.append(submission.description.strip())
    if submission.location and submission.location.strip():
        parts.append(f"📍 {submission.location.strip()}")
    return "\n\n".join(parts)


def _build_raw_text(submission: OpportunitySubmission) -> str:
    lines = [
        submission.title or "Возможность от пользователя",
        "",
        _build_description(submission) or "",
    ]
    if submission.deadline:
        lines.append(f"\nДедлайн: {_format_deadline(submission.deadline)}")
    if submission.link:
        lines.append(f"\nСсылка: {submission.link}")
    return "\n".join(line for line in lines if line is not None).strip()


async def ensure_community_channel(session: AsyncSession) -> MonitoredChannel:
    result = await session.execute(
        select(MonitoredChannel).where(
            MonitoredChannel.channel_identifier == COMMUNITY_CHANNEL_IDENTIFIER
        )
    )
    channel = result.scalar_one_or_none()
    if channel:
        if not channel.is_seed:
            channel.is_seed = True
            channel.is_accessible = True
            await session.flush()
        return channel

    channel = MonitoredChannel(
        channel_identifier=COMMUNITY_CHANNEL_IDENTIFIER,
        channel_title=COMMUNITY_CHANNEL_TITLE,
        is_seed=True,
        is_accessible=True,
        source_count=0,
    )
    session.add(channel)
    await session.flush()
    return channel


async def approve_submission(session: AsyncSession, submission_id: int) -> CatalogOpportunity:
    repo = SubmissionRepository(session)
    submission = await repo.get_by_id(submission_id)
    if not submission:
        raise ValueError("not_found")
    if submission.status != "pending":
        raise ValueError("already_reviewed")

    channel = await ensure_community_channel(session)
    message_link = (submission.link or "").strip() or f"lumo://submission/{submission.id}"
    raw_message = RawMessage(
        monitored_channel_id=channel.id,
        telegram_message_id=-submission.id,
        text=_build_raw_text(submission),
        message_link=message_link,
        posted_at=datetime.now(timezone.utc),
    )
    session.add(raw_message)
    await session.flush()

    opp_type = (submission.opportunity_type or "конкурс").lower().strip()
    if opp_type == "другое":
        opp_type = "конкурс"

    title = (submission.title or "").strip()
    if not title:
        link = (submission.link or "").strip()
        title = f"Пост из канала" if submission.source_mode == "channel" else "Возможность"
        if link:
            title = link[:120]
    catalog_repo = OpportunityCatalogRepository(session)
    entry = await catalog_repo.create_manual_active(
        raw_message=raw_message,
        channel=channel,
        opportunity_type=opp_type,
        title=title[:512],
        description=_build_description(submission) or title,
        deadline=_format_deadline(submission.deadline),
        application_url=(submission.link or "").strip() or None,
    )

    await repo.mark_reviewed(submission, status="approved", catalog_id=entry.id)
    return entry


async def reject_submission(
    session: AsyncSession,
    submission_id: int,
    *,
    admin_note: str | None = None,
) -> OpportunitySubmission:
    repo = SubmissionRepository(session)
    submission = await repo.get_by_id(submission_id)
    if not submission:
        raise ValueError("not_found")
    if submission.status != "pending":
        raise ValueError("already_reviewed")
    return await repo.mark_reviewed(submission, status="rejected", admin_note=admin_note)


def serialize_submission(row: OpportunitySubmission, *, include_user: bool = False) -> dict:
    payload = {
        "id": row.id,
        "sourceMode": row.source_mode,
        "title": row.title,
        "type": row.opportunity_type,
        "description": row.description,
        "deadline": row.deadline,
        "location": row.location,
        "link": row.link,
        "status": row.status,
        "catalogId": row.catalog_id,
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "reviewedAt": row.reviewed_at.isoformat() if row.reviewed_at else None,
    }
    if include_user and row.user:
        user: User = row.user
        payload["username"] = user.username
        payload["telegramId"] = user.telegram_id
    return payload

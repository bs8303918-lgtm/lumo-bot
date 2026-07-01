"""Admin tracking dashboard payload for Mini App."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from db.repositories.admin_analytics import AdminAnalyticsRepository
from db.repositories.users import SystemStateRepository
from services.subscription_stats import build_subscription_stats


def _format_ago_minutes(iso_value: str | None) -> str:
    if not iso_value:
        return "давно"
    try:
        dt = datetime.fromisoformat(iso_value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return "давно"
    delta = datetime.now(timezone.utc) - dt
    minutes = int(delta.total_seconds() // 60)
    if minutes < 1:
        return "только что"
    if minutes < 60:
        return f"{minutes} мин назад"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} ч назад"
    days = hours // 24
    return f"{days} дн назад"


def _scan_message(event_type: str, meta: dict) -> tuple[str, str]:
    channel = meta.get("channel") or meta.get("identifier") or ""
    channel_ref = f"@{channel}" if channel and not str(channel).startswith("@") else channel

    if event_type == "channel_scan":
        new_posts = meta.get("newPosts", 0)
        return "ok", f"{channel_ref} — {new_posts} новых постов"
    if event_type == "monitor_cycle_success":
        channels = meta.get("channels", 0)
        posts = meta.get("postsToday")
        if posts is not None:
            return "ok", f"Полный скан завершён — {channels} каналов, {posts} постов"
        return "ok", f"Полный скан завершён — {channels} каналов"
    if event_type == "telethon_flood_wait":
        seconds = meta.get("seconds", 60)
        return "error", f"{channel_ref} — Telethon FloodWait {seconds}s, пропущен"
    if event_type == "channel_unavailable":
        retry = meta.get("retryIn", "1ч")
        return "warn", f"{channel_ref} — канал недоступен, retry через {retry}"
    return "ok", str(meta)


async def build_tracking_dashboard(session: AsyncSession) -> dict:
    settings = get_settings()
    repo = AdminAnalyticsRepository(session)
    state_repo = SystemStateRepository(session)

    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)

    total_users = await repo.count_users()
    users_week = await repo.count_users_since(week_ago)
    active_users = await repo.count_active_users_since(week_ago)
    active_prev = await repo.count_active_users_since(week_ago - timedelta(days=7))
    active_delta = active_users - active_prev

    channels = await repo.count_monitored_channels()
    new_channels = await repo.count_new_channels_since(week_ago)

    posts_today = await repo.count_posts_since(today_start)
    posts_yesterday = await repo.count_posts_since(yesterday_start) - posts_today
    posts_delta = posts_today - max(posts_yesterday, 0)

    ai_today = await repo.count_ai_requests_since(today_start)
    ai_users = await repo.count_ai_users_since(today_start)
    ai_avg = round(ai_today / ai_users, 1) if ai_users else 0.0
    ai_chart = await repo.ai_requests_by_hour_today()

    last_monitor = await state_repo.get("last_monitor_success_at")
    monitor_hours = max(1, settings.monitor_interval_minutes // 60)
    monitor_label = f"Авто каждые {monitor_hours}ч" if monitor_hours < 24 else "Авто каждые 24ч"

    scan_rows = await repo.scan_log(limit=12)
    scan_log = []
    for row in scan_rows:
        status, message = _scan_message(row["type"], row.get("meta") or {})
        at = row.get("at")
        time_label = ""
        if at:
            try:
                dt = datetime.fromisoformat(at)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                time_label = dt.astimezone(timezone.utc).strftime("%H:%M")
            except ValueError:
                time_label = ""
        scan_log.append({"time": time_label, "status": status, "message": message})

    feedback_items, unread_feedback = await repo.feedback_list(limit=8)

    from db.repositories.submissions import SubmissionRepository

    submission_repo = SubmissionRepository(session)
    pending_submissions = await submission_repo.list_by_status("pending", limit=8)
    pending_submissions_count = await submission_repo.count_pending()
    submission_items = [
        {
            "id": row.id,
            "sourceMode": row.source_mode,
            "title": row.title,
            "type": row.opportunity_type,
            "description": row.description,
            "deadline": row.deadline,
            "location": row.location,
            "link": row.link,
            "username": row.user.username if row.user else None,
            "telegramId": row.user.telegram_id if row.user else None,
            "createdAt": row.created_at.isoformat() if row.created_at else None,
        }
        for row in pending_submissions
    ]

    sub_stats = await build_subscription_stats(session)

    return {
        "updatedAgo": _format_ago_minutes(last_monitor),
        "monitorSchedule": monitor_label,
        "metrics": {
            "users": {"total": total_users, "deltaWeek": users_week},
            "active": {"total": active_users, "deltaWeek": active_delta},
            "channels": {"total": channels, "deltaWeek": new_channels},
            "postsToday": {"total": posts_today, "deltaYesterday": posts_delta},
        },
        "aiToday": {
            "total": ai_today,
            "avgPerUser": ai_avg,
            "chart": ai_chart,
        },
        "recentUsers": await repo.recent_users(limit=8),
        "topChannels": await repo.top_channels_by_users(limit=8),
        "scanLog": scan_log,
        "feedback": feedback_items,
        "unreadFeedback": unread_feedback,
        "submissions": submission_items,
        "pendingSubmissions": pending_submissions_count,
        "subscriptions": {
            "totalUsers": sub_stats["totalUsers"],
            "startifyUsers": sub_stats["startifyUsers"],
            "everPaidRetail": sub_stats["everPaidRetail"],
            "activePaidRetail": sub_stats["activePaidRetail"],
            "activeTrial": sub_stats["activeTrial"],
            "expiredTrial": sub_stats["expiredTrial"],
            "freemium": sub_stats["freemium"],
            "byPlan": sub_stats["byPlan"],
            "activeByPlan": sub_stats["activeByPlan"],
            "revenueActiveKzt": sub_stats["revenueActiveKzt"],
        },
    }

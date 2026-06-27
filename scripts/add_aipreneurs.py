"""Разово добавить AI'preneurs в каталог — без мониторинга канала."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from db.base import async_session_factory
from db.models import RawMessage
from db.repositories.opportunity_catalog import OpportunityCatalogRepository
from services.opportunity_catalog import OpportunityCatalogService
from services.notification_service import NotificationService
from services.submission_service import ensure_community_channel


async def main() -> None:
    deadline = (datetime.now(timezone.utc) + timedelta(hours=24)).strftime("%d.%m.%Y")
    message_link = "https://t.me/KBTUstartup/1818"
    title = "AI'preneurs — акселератор AI-предпринимателей (5-й поток, Алматы)"
    description = (
        "Программа Astana Hub и Almaty Hub: от идеи до работающего AI-продукта. "
        "5-й поток впервые в Алматы (Almaty Hub), 14 недель — команды, MVP, выход на рынок. "
        "Конкурсный отбор. ⏰ Дедлайн заявок ~24 часа."
    )

    async with async_session_factory() as session:
        channel = await ensure_community_channel(session)
        catalog_repo = OpportunityCatalogRepository(session)

        dup = await catalog_repo.find_active_duplicate(title, message_link, description)
        if dup:
            print(f"Уже в каталоге: id={dup.id} deadline={dup.deadline}")
            catalog_id = dup.id
            await session.commit()
        else:
            raw_message = RawMessage(
                monitored_channel_id=channel.id,
                telegram_message_id=-1818,
                text=f"{title}\n\n{description}\n\n{message_link}",
                message_link=message_link,
                posted_at=datetime.now(timezone.utc),
            )
            session.add(raw_message)
            await session.flush()

            entry = await catalog_repo.create_manual_active(
                raw_message=raw_message,
                channel=channel,
                opportunity_type="конкурс",
                title=title,
                description=description,
                deadline=deadline,
                application_url=message_link,
                requirements="Основатели стартапов, AI/продуктовые специалисты",
            )
            entry.source_channel_name = "KBTU Startup Incubator (@KBTUstartup)"
            await session.commit()
            catalog_id = entry.id
            print(f"Добавлено: id={catalog_id} deadline={deadline}")

    n = await OpportunityCatalogService(NotificationService()).notify_users_for_catalog_item(catalog_id)
    print(f"Уведомлено пользователей: {n}")


if __name__ == "__main__":
    asyncio.run(main())

import json

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Course, ExpertService, Grant

SEED_GRANTS = [
    {
        "flag": "🇿🇦",
        "location": "ЮАР | Audi Foundation",
        "title": "Audi Environmental Foundation 2026",
        "description": (
            "Вы — молодой лидер, работающий над экологическими проблемами? "
            "Шанс попасть на One Young World Summit 2026 в Кейптауне."
        ),
        "deadline": "1 июня",
        "features": ["Полное покрытие (Full Ride)", "Лидеры 18–30 лет"],
        "is_premium": False,
        "application_url": "https://www.audifoundation.com/environmental-foundation/",
        "message_link": None,
        "requirements": "Возраст 18–30, проект в области экологии или устойчивого развития.",
        "document_templates": ["Мотивационное письмо", "CV на английском"],
    },
    {
        "flag": "🇯🇵",
        "location": "Япония | Правительство",
        "title": "MEXT Scholarship 2027",
        "description": (
            "Самая престижная стипендия Японии. Полное финансирование обучения, "
            "проживания и перелета. Без вступительных взносов."
        ),
        "deadline": "Скоро",
        "features": ["Авиабилеты", "Ежемесячная стипендия"],
        "is_premium": True,
        "application_url": "https://www.studyinjapan.go.jp/en/",
        "message_link": "https://t.me/opportunities_zula/123",
        "requirements": "Бакалавриат или магистратура, GPA от 3.0, возраст до 35 лет.",
        "document_templates": ["Research Plan", "Letter of Recommendation", "Transcript"],
    },
    {
        "flag": "🇰🇬",
        "location": "Кыргызстан | ЕС",
        "title": "Программа ЕС PROSPECTS",
        "description": (
            "Финансирование инфраструктурных и энергетических проектов в городах Кыргызстана. "
            "Выход на гранты в миллионы евро."
        ),
        "deadline": "Активно",
        "features": ["Для команд", "Энергоэффективность"],
        "is_premium": False,
        "application_url": "https://prospects-eu.org/",
        "message_link": None,
        "requirements": "Команда из 2+ человек, проект в сфере энергоэффективности или инфраструктуры.",
        "document_templates": ["Project proposal", "Budget template"],
    },
]

SEED_SERVICES = [
    {"title": "Консультация", "price_display": "70К ₸", "sort_order": 1},
    {"title": "Сопровождение", "price_display": "300К ₸", "sort_order": 2},
]

SEED_COURSES = [
    {
        "title": "Видеокурс: Гранты 2026",
        "description": "Пошаговый план: как выигрывать полные стипендии с нуля.",
        "price_display": "10 000 ₸",
    },
]


async def seed_catalog_if_empty(session: AsyncSession) -> None:
    grant_count = await session.scalar(select(func.count()).select_from(Grant))
    if not grant_count:
        for item in SEED_GRANTS:
            session.add(
                Grant(
                    flag=item["flag"],
                    location=item["location"],
                    title=item["title"],
                    description=item["description"],
                    deadline=item["deadline"],
                    features_json=json.dumps(item["features"], ensure_ascii=False),
                    is_premium=item["is_premium"],
                    application_url=item["application_url"],
                    message_link=item["message_link"],
                    requirements=item["requirements"],
                    document_templates_json=json.dumps(item["document_templates"], ensure_ascii=False),
                )
            )

    service_count = await session.scalar(select(func.count()).select_from(ExpertService))
    if not service_count:
        for item in SEED_SERVICES:
            session.add(ExpertService(**item))

    course_count = await session.scalar(select(func.count()).select_from(Course))
    if not course_count:
        for item in SEED_COURSES:
            session.add(Course(**item))

    await session.flush()


async def main() -> None:
    from db.base import Base, async_session_factory, engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        await seed_catalog_if_empty(session)
        await session.commit()
        print("Catalog seeded.")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())

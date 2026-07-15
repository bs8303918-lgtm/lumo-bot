"""
Демо-аккаунты студента и ментора с уже связанной комнатой.

Запуск из корня репозитория:
  python scripts/seed_demo_room_accounts.py

Логины (пароль у обоих: LumoDemo123):
  student — demo-student@lumo.demo
  mentor  — demo-mentor@lumo.demo
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db.base import async_session_factory
from db.models import User
from db.repositories.shared_rooms import SharedRoomRepository
from db.repositories.users import UserRepository
from services.subscription import PLAN_12M
from services.web_auth import email_telegram_id, hash_password

STUDENT_EMAIL = "demo-student@lumo.demo"
MENTOR_EMAIL = "demo-mentor@lumo.demo"
DEMO_PASSWORD = "LumoDemo123"


async def _ensure_user(
    repo: UserRepository,
    *,
    email: str,
    display_name: str,
    role: str,
    paid: bool = False,
) -> User:
    existing = await repo.get_by_email(email)
    expires = datetime.now(timezone.utc) + timedelta(days=365) if paid else None
    plan = PLAN_12M if paid else "freemium"

    if existing:
        existing.display_name = display_name
        existing.role = role
        if not existing.password_hash:
            existing.password_hash = hash_password(DEMO_PASSWORD)
        if paid:
            existing.tariff_plan = plan
            existing.tariff_expires_at = expires
        return existing

    user, _ = await repo.create_web_user(
        email=email,
        password_hash=hash_password(DEMO_PASSWORD),
        display_name=display_name,
        telegram_id=email_telegram_id(email),
    )
    user.role = role
    if paid:
        user.tariff_plan = plan
        user.tariff_expires_at = expires
    return user


async def main() -> None:
    async with async_session_factory() as session:
        users = UserRepository(session)
        rooms = SharedRoomRepository(session)

        student = await _ensure_user(
            users,
            email=STUDENT_EMAIL,
            display_name="Демо Студент",
            role="student",
            paid=True,
        )
        mentor = await _ensure_user(
            users,
            email=MENTOR_EMAIL,
            display_name="Демо Ментор",
            role="mentor",
            paid=True,
        )

        room = await rooms.get_or_create_for_student(student.id)
        await rooms.bind_mentor(room, mentor)

        await session.commit()

    print("Готово. Демо-аккаунты:")
    print(f"  Студент: {STUDENT_EMAIL} / {DEMO_PASSWORD}")
    print(f"  Ментор:  {MENTOR_EMAIL} / {DEMO_PASSWORD}")
    print(f"  Комната: student_id={student.id}, mentor_id={mentor.id}, room_id={room.id}")
    print()
    print("Как посмотреть UI:")
    print("  1. Открой /app → Войти → demo-student@lumo.demo → вкладка «Мой ментор»")
    print("  2. Инкогнито → /app → demo-mentor@lumo.demo → вкладка «Менторы» (CRM-канбан)")


if __name__ == "__main__":
    asyncio.run(main())

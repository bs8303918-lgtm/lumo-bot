"""Access control for mentor «room» context on catalog and AI search."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from db.models import SharedRoom, User
from db.repositories.shared_rooms import SharedRoomRepository
from db.repositories.users import UserRepository
from services.subscription import is_paid_plan_active


ROLE_MENTOR = "mentor"
ROLE_STUDENT = "student"
ROOM_HEADER = "X-Room-Student-Id"


@dataclass
class RoomContext:
    actor: User
    student: User
    room: SharedRoom


def user_is_mentor(user: User) -> bool:
    return (user.role or ROLE_STUDENT).lower() == ROLE_MENTOR


def student_subscription_active(student: User) -> bool:
    settings = get_settings()
    if not settings.subscriptions_enforced:
        return True
    return is_paid_plan_active(student)


def _parse_room_student_id(raw: str | int | None) -> int | None:
    if raw is None or raw == "":
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Некорректный ID комнаты студента") from exc
    if value < 1:
        raise HTTPException(status_code=422, detail="Некорректный ID комнаты студента")
    return value


def mentor_subscription_active(user: User) -> bool:
    return student_subscription_active(user)


async def resolve_room_context(
    session: AsyncSession,
    actor: User,
    room_student_id: int | None,
) -> RoomContext | None:
    """
    Returns RoomContext when mentor operates inside a paid student room.
    Returns None for students, admins, and mentor personal workspace (no room header).
    Raises 403 when mentor opens a room whose student subscription is inactive.
    """
    settings = get_settings()
    if settings.user_is_admin(actor.telegram_id, actor.email):
        return None

    if not user_is_mentor(actor):
        return None

    student_id = _parse_room_student_id(room_student_id)
    if student_id is None:
        return None

    rooms = SharedRoomRepository(session)
    room = await rooms.get_mentor_room(actor.id, student_id)
    if not room:
        raise HTTPException(status_code=403, detail="Нет доступа к комнате этого студента")

    student = await UserRepository(session).get_by_id(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Студент не найден")

    if not student_subscription_active(student):
        raise HTTPException(
            status_code=403,
            detail="Подписка студента неактивна — поиск в этой комнате недоступен. "
            "Используй «Мой стол» и свою подписку ментора.",
        )

    return RoomContext(actor=actor, student=student, room=room)


async def effective_catalog_user(
    session: AsyncSession,
    actor: User,
    room_student_id: int | None,
) -> User:
    """User whose catalog scope and interest profile apply to the request."""
    settings = get_settings()
    ctx = await resolve_room_context(session, actor, room_student_id)
    if ctx:
        return ctx.student

    if user_is_mentor(actor) and not settings.user_is_admin(actor.telegram_id, actor.email):
        if not mentor_subscription_active(actor):
            raise HTTPException(
                status_code=403,
                detail="Нужна активная подписка ментора для поиска в личном кабинете",
            )
        return actor

    return actor


def read_room_student_id_header(
    x_room_student_id: str | None = Header(default=None, alias=ROOM_HEADER),
    room_student_id: int | None = None,
) -> int | None:
    """Query param `room_student_id` overrides header for simple GET links."""
    if room_student_id is not None:
        return _parse_room_student_id(room_student_id)
    if x_room_student_id is None or not str(x_room_student_id).strip():
        return None
    return _parse_room_student_id(x_room_student_id)

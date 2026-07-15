"""Shared rooms (student ↔ mentor collaborative workspace)."""

from __future__ import annotations

import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import SharedRoom, User


def new_invite_token() -> str:
    return secrets.token_urlsafe(32)


class SharedRoomRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, room_id: int) -> SharedRoom | None:
        result = await self.session.execute(select(SharedRoom).where(SharedRoom.id == room_id))
        return result.scalar_one_or_none()

    async def get_by_student_id(self, student_id: int) -> SharedRoom | None:
        result = await self.session.execute(
            select(SharedRoom).where(SharedRoom.student_id == student_id)
        )
        return result.scalar_one_or_none()

    async def get_by_token(self, token: str) -> SharedRoom | None:
        result = await self.session.execute(
            select(SharedRoom).where(SharedRoom.invite_token == token.strip())
        )
        return result.scalar_one_or_none()

    async def get_mentor_room(self, mentor_id: int, student_id: int) -> SharedRoom | None:
        result = await self.session.execute(
            select(SharedRoom).where(
                SharedRoom.mentor_id == mentor_id,
                SharedRoom.student_id == student_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_mentor(self, mentor_id: int) -> list[SharedRoom]:
        result = await self.session.execute(
            select(SharedRoom)
            .where(SharedRoom.mentor_id == mentor_id)
            .options(selectinload(SharedRoom.student))
            .order_by(SharedRoom.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_or_create_for_student(self, student_id: int) -> SharedRoom:
        room = await self.get_by_student_id(student_id)
        if room:
            return room
        room = SharedRoom(
            student_id=student_id,
            invite_token=new_invite_token(),
        )
        self.session.add(room)
        await self.session.flush()
        return room

    async def rotate_invite_token(self, room: SharedRoom) -> SharedRoom:
        room.invite_token = new_invite_token()
        await self.session.flush()
        return room

    async def bind_mentor(self, room: SharedRoom, mentor: User) -> SharedRoom:
        room.mentor_id = mentor.id
        room.pending_mentor_email = None
        if (mentor.role or "student") != "mentor":
            mentor.role = "mentor"
        await self.session.flush()
        return room

    async def revoke_mentor(self, room: SharedRoom) -> SharedRoom:
        room.mentor_id = None
        room.invite_token = new_invite_token()
        await self.session.flush()
        return room

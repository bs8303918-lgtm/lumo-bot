"""Shared rooms API — invite mentor, accept, list, revoke."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from api.deps import get_db
from config import get_settings
from db.models import User
from db.repositories.shared_rooms import SharedRoomRepository
from db.repositories.users import UserRepository
from db.repositories.mentor_workspace import KANBAN_STATUSES, MentorWorkspaceRepository
from services.opportunity_catalog import catalog_repo
from services.shared_room_access import ROLE_MENTOR, student_subscription_active
from services.subscription import subscription_status
from services.webapp_catalog import serialize_opportunity

router = APIRouter(tags=["rooms"])

KANBAN_LABELS = {
    "todo": "Нужно подать",
    "in_progress": "В процессе",
    "submitted": "Подано",
}

STATUS_STYLES = {
    "todo": "amber",
    "in_progress": "blue",
    "submitted": "emerald",
}


class InviteRequest(BaseModel):
    mentorEmail: str | None = Field(default=None, max_length=255)


class AcceptRequest(BaseModel):
    roomId: int = Field(ge=1)
    token: str = Field(min_length=8, max_length=128)


def _display_name(user: User) -> str:
    if user.display_name and user.display_name.strip():
        return user.display_name.strip()
    if user.username and user.username.strip():
        return user.username.strip()
    if user.email and user.email.strip():
        return user.email.split("@")[0]
    return "Студент"


def _serialize_room(room, *, student: User | None = None, mentor: User | None = None) -> dict:
    sub = subscription_status(student) if student else None
    return {
        "id": room.id,
        "studentId": room.student_id,
        "mentorId": room.mentor_id,
        "pendingMentorEmail": room.pending_mentor_email,
        "createdAt": room.created_at.isoformat() if room.created_at else None,
        "studentName": _display_name(student) if student else None,
        "mentorName": _display_name(mentor) if mentor else None,
        "mentorEmail": mentor.email if mentor else room.pending_mentor_email,
        "subscriptionActive": bool(sub and sub.get("isActive")),
        "subscription": sub,
    }


def _invite_path(room_id: int, token: str) -> str:
    return f"/invite?room={room_id}&token={token}"


@router.get("/rooms/meta")
async def rooms_meta() -> dict:
    settings = get_settings()
    origins = [o.strip().rstrip("/") for o in settings.api_cors_origins.split(",") if o.strip()]
    site_base = origins[0] if origins else ""
    return {
        "invitePathTemplate": "/invite?room={roomId}&token={token}",
        "siteBaseUrl": site_base,
        "roomHeader": "X-Room-Student-Id",
    }


@router.get("/rooms/my")
async def my_room(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    if (user.role or "student") == ROLE_MENTOR:
        raise HTTPException(status_code=403, detail="Доступно только студентам")

    rooms = SharedRoomRepository(session)
    room = await rooms.get_or_create_for_student(user.id)
    mentor = None
    if room.mentor_id:
        mentor = await UserRepository(session).get_by_id(room.mentor_id)
    await session.commit()

    payload = _serialize_room(room, student=user, mentor=mentor)
    payload["invitePath"] = _invite_path(room.id, room.invite_token)
    payload["hasActiveSubscription"] = student_subscription_active(user)
    return payload


@router.post("/rooms/invite")
async def invite_mentor(
    payload: InviteRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    if (user.role or "student") == ROLE_MENTOR:
        raise HTTPException(status_code=403, detail="Только студент может пригласить ментора")

    if not student_subscription_active(user):
        raise HTTPException(
            status_code=403,
            detail="Нужна активная подписка, чтобы открыть совместный доступ ментору",
        )

    email = (payload.mentorEmail or "").strip().lower() or None
    if email and ("@" not in email or "." not in email.split("@")[-1]):
        raise HTTPException(status_code=422, detail="Некорректный email ментора")

    rooms = SharedRoomRepository(session)
    room = await rooms.get_or_create_for_student(user.id)
    if email:
        room.pending_mentor_email = email
    await session.commit()

    mentor = None
    if room.mentor_id:
        mentor = await UserRepository(session).get_by_id(room.mentor_id)

    result = _serialize_room(room, student=user, mentor=mentor)
    result["invitePath"] = _invite_path(room.id, room.invite_token)
    result["message"] = (
        "Ссылка готова — отправь её ментору"
        if not room.mentor_id
        else "Ментор уже подключён. Новая ссылка для смены ментора — после отзыва доступа."
    )
    return result


@router.delete("/rooms/mentor")
async def revoke_mentor(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    rooms = SharedRoomRepository(session)
    room = await rooms.get_by_student_id(user.id)
    if not room:
        raise HTTPException(status_code=404, detail="Комната не найдена")

    await rooms.revoke_mentor(room)
    await session.commit()

    return {
        "ok": True,
        "invitePath": _invite_path(room.id, room.invite_token),
        "message": "Доступ ментора отозван",
    }


@router.get("/rooms/as-mentor")
async def mentor_rooms(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    rooms = SharedRoomRepository(session)
    items = await rooms.list_for_mentor(user.id)
    payload = []
    for room in items:
        student = room.student
        payload.append(
            {
                **_serialize_room(room, student=student, mentor=user),
                "canSearch": student_subscription_active(student) if student else False,
            }
        )
    return {"rooms": payload, "count": len(payload)}


@router.get("/rooms/preview")
async def preview_invite(
    room: int = Query(..., ge=1, alias="room"),
    token: str = Query(..., min_length=8),
    session: AsyncSession = Depends(get_db),
) -> dict:
    rooms = SharedRoomRepository(session)
    row = await rooms.get_by_id(room)
    if not row or row.invite_token != token.strip():
        raise HTTPException(status_code=404, detail="Ссылка недействительна или устарела")

    student = await UserRepository(session).get_by_id(row.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Студент не найден")

    already_bound = row.mentor_id is not None
    return {
        "roomId": row.id,
        "studentId": row.student_id,
        "studentName": _display_name(student),
        "subscriptionActive": student_subscription_active(student),
        "alreadyHasMentor": already_bound,
        "valid": True,
    }


@router.post("/rooms/accept")
async def accept_invite(
    payload: AcceptRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    rooms = SharedRoomRepository(session)
    row = await rooms.get_by_id(payload.roomId)
    if not row or row.invite_token != payload.token.strip():
        raise HTTPException(status_code=404, detail="Ссылка недействительна или устарела")

    student = await UserRepository(session).get_by_id(row.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Студент не найден")

    if not student_subscription_active(student):
        raise HTTPException(
            status_code=403,
            detail="Подписка студента неактивна — войти в комнату пока нельзя",
        )

    if row.student_id == user.id:
        raise HTTPException(status_code=400, detail="Студент не может принять приглашение в свою комнату")

    if row.mentor_id and row.mentor_id != user.id:
        raise HTTPException(
            status_code=409,
            detail="У этого студента уже есть другой ментор. Попроси новую ссылку после отзыва доступа.",
        )

    await rooms.bind_mentor(row, user)
    await session.commit()

    return {
        "ok": True,
        "roomId": row.id,
        "studentId": row.student_id,
        "studentName": _display_name(student),
        "message": f"Вы в комнате студента {_display_name(student)}",
    }


class StudentProposalUpdate(BaseModel):
    status: str = Field(pattern="^(todo|in_progress|submitted)$")


async def _serialize_student_proposal(session: AsyncSession, student: User, app) -> dict:
    repo = catalog_repo(session)
    row = await repo.get_entry_with_channel(app.catalog_id)
    if not row:
        raise HTTPException(status_code=404, detail="Программа не найдена")
    entry, _channel = row
    if not entry.is_active:
        raise HTTPException(status_code=404, detail="Программа не найдена")
    if not await repo.user_can_access_entry(student.id, entry.id):
        raise HTTPException(status_code=403, detail="Нет доступа к программе")
    opp = serialize_opportunity(entry)
    return {
        "id": app.id,
        "catalogId": app.catalog_id,
        "status": app.status,
        "statusLabel": KANBAN_LABELS.get(app.status, app.status),
        "notes": app.notes,
        "updatedAt": app.updated_at.isoformat() if app.updated_at else None,
        "opportunity": {
            "id": opp["id"],
            "title": opp["title"],
            "type": opp["type"],
            "label": opp["label"],
            "emoji": opp["emoji"],
            "deadlineLabel": opp["deadlineLabel"],
            "deadlineUrgent": opp["deadlineUrgent"],
            "applicationUrl": opp.get("applicationUrl"),
            "messageLink": opp.get("messageLink"),
            "channelUrl": opp.get("channelUrl"),
        },
    }


@router.get("/rooms/my/proposals")
async def student_proposals(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    if (user.role or "student") == ROLE_MENTOR:
        raise HTTPException(status_code=403, detail="Доступно только студентам")

    rooms = SharedRoomRepository(session)
    room = await rooms.get_by_student_id(user.id)
    if not room or not room.mentor_id:
        return {"items": [], "total": 0, "mentor": None, "stats": {"todo": 0, "in_progress": 0, "submitted": 0}}

    mentor = await UserRepository(session).get_by_id(room.mentor_id)
    workspace = MentorWorkspaceRepository(session)
    apps = await workspace.list_applications_for_student(room.mentor_id, user.id)
    legacy = await workspace.list_applications_by_name(room.mentor_id, _display_name(user))
    seen = {a.id for a in apps}
    for app in legacy:
        if app.id not in seen:
            if not app.student_user_id:
                app.student_user_id = user.id
            apps.append(app)
            seen.add(app.id)
    await session.flush()
    items = []
    for app in apps:
        try:
            items.append(await _serialize_student_proposal(session, user, app))
        except HTTPException:
            continue

    stats = {
        "todo": sum(1 for i in items if i["status"] == "todo"),
        "in_progress": sum(1 for i in items if i["status"] == "in_progress"),
        "submitted": sum(1 for i in items if i["status"] == "submitted"),
    }
    return {
        "items": items,
        "total": len(items),
        "mentor": {
            "id": mentor.id if mentor else room.mentor_id,
            "name": _display_name(mentor) if mentor else None,
            "email": mentor.email if mentor else None,
        },
        "stats": stats,
    }


@router.patch("/rooms/my/proposals/{app_id}")
@router.post("/rooms/my/proposals/{app_id}/status")
async def update_student_proposal(
    app_id: int,
    body: StudentProposalUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    if body.status not in KANBAN_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")

    rooms = SharedRoomRepository(session)
    room = await rooms.get_by_student_id(user.id)
    if not room or not room.mentor_id:
        raise HTTPException(status_code=404, detail="Ментор не подключён")

    workspace = MentorWorkspaceRepository(session)
    app = await workspace.get_application_for_student(room.mentor_id, user.id, app_id)
    if not app:
        app = await workspace.get_application_by_id(room.mentor_id, app_id)
        if app and not app.student_user_id:
            app.student_user_id = user.id
            await session.flush()
        elif not app or app.student_user_id not in (None, user.id):
            raise HTTPException(status_code=404, detail="Предложение не найдено")
    if not app:
        raise HTTPException(status_code=404, detail="Предложение не найдено")

    app = await workspace.update_application(app, status=body.status)
    await session.commit()
    return {"application": await _serialize_student_proposal(session, user, app)}

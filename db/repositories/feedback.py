from sqlalchemy.ext.asyncio import AsyncSession

from db.models import UserFeedback


class FeedbackRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        *,
        kind: str,
        message: str,
        user_id: int | None = None,
        username: str | None = None,
        source: str = "mini_app",
    ) -> UserFeedback:
        row = UserFeedback(
            user_id=user_id,
            username=username,
            kind=kind,
            message=message.strip(),
            source=source,
        )
        self.session.add(row)
        await self.session.flush()
        return row

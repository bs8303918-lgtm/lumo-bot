import asyncio
import json
from pathlib import Path

from db.base import async_session_factory
from db.repositories.users import UserRepository
from services.interest_stats import _user_categories

OUT = Path(__file__).resolve().parent.parent / "data" / "interest_profiles_export.json"


async def main() -> None:
    async with async_session_factory() as session:
        users = await UserRepository(session).list_with_interests()
    users.sort(key=lambda u: u.id)

    rows = []
    for i, user in enumerate(users, 1):
        rows.append(
            {
                "n": i,
                "db_id": user.id,
                "telegram_id": user.telegram_id,
                "username": user.username,
                "categories": _user_categories(user),
                "interest_query": user.interest_query or "",
            }
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"written {len(rows)} -> {OUT}")


if __name__ == "__main__":
    asyncio.run(main())

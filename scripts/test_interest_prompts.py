import asyncio

from db.base import async_session_factory
from services.admin_interest_prompts import build_interest_prompts_dashboard


async def main() -> None:
    async with async_session_factory() as session:
        data = await build_interest_prompts_dashboard(session, limit=3)
    print("withInterest", data["withInterest"], "items", len(data["items"]))
    if data["items"]:
        item = data["items"][0]
        print(item["query"][:80])
        print([t["label"] for t in item["types"]])
        print([d["label"] for d in item["domains"]])


asyncio.run(main())

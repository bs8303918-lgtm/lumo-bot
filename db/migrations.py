from sqlalchemy import text

from db.base import engine


async def ensure_user_columns() -> None:
    if not str(engine.url).startswith("sqlite"):
        return
    async with engine.begin() as conn:
        result = await conn.execute(text("PRAGMA table_info(users)"))
        columns = {row[1] for row in result.fetchall()}
        if "interest_categories_json" not in columns:
            await conn.execute(text("ALTER TABLE users ADD COLUMN interest_categories_json TEXT"))
        if "notifications_enabled" not in columns:
            await conn.execute(
                text("ALTER TABLE users ADD COLUMN notifications_enabled BOOLEAN NOT NULL DEFAULT 1")
            )
        if "interest_preferences_json" not in columns:
            await conn.execute(text("ALTER TABLE users ADD COLUMN interest_preferences_json TEXT"))


async def ensure_raw_message_columns() -> None:
    if not str(engine.url).startswith("sqlite"):
        return
    async with engine.begin() as conn:
        result = await conn.execute(text("PRAGMA table_info(raw_messages)"))
        columns = {row[1] for row in result.fetchall()}
        if "posted_at" not in columns:
            await conn.execute(text("ALTER TABLE raw_messages ADD COLUMN posted_at DATETIME"))


async def ensure_catalog_columns() -> None:
    if not str(engine.url).startswith("sqlite"):
        return
    async with engine.begin() as conn:
        result = await conn.execute(text("PRAGMA table_info(catalog_opportunities)"))
        columns = {row[1] for row in result.fetchall()}
        if "tags_json" not in columns:
            await conn.execute(text("ALTER TABLE catalog_opportunities ADD COLUMN tags_json TEXT"))

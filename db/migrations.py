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


async def ensure_catalog_multi_per_message() -> None:
    """Allow several catalog cards from one Telegram post (grant roundups)."""
    dialect = engine.dialect.name
    async with engine.begin() as conn:
        if dialect == "postgresql":
            await conn.execute(
                text(
                    "ALTER TABLE catalog_opportunities "
                    "DROP CONSTRAINT IF EXISTS catalog_opportunities_raw_message_id_key"
                )
            )
            await conn.execute(
                text("DROP INDEX IF EXISTS ix_catalog_opportunities_raw_message_id")
            )
        elif dialect == "sqlite":
            result = await conn.execute(
                text(
                    "SELECT sql FROM sqlite_master "
                    "WHERE type='table' AND name='catalog_opportunities'"
                )
            )
            row = result.fetchone()
            if not row or not row[0]:
                return
            ddl = row[0]
            if "raw_message_id" in ddl and "UNIQUE" in ddl.upper():
                await conn.execute(text("ALTER TABLE catalog_opportunities RENAME TO catalog_opportunities_old"))
                await conn.execute(
                    text(
                        """
                        CREATE TABLE catalog_opportunities (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            raw_message_id INTEGER NOT NULL REFERENCES raw_messages(id) ON DELETE CASCADE,
                            opportunity_type VARCHAR(64) NOT NULL,
                            tags_json TEXT,
                            title VARCHAR(512) NOT NULL,
                            deadline VARCHAR(128) NOT NULL,
                            description TEXT NOT NULL,
                            requirements TEXT,
                            application_url VARCHAR(512),
                            source_channel_name VARCHAR(255) NOT NULL,
                            message_link VARCHAR(512) NOT NULL,
                            is_active BOOLEAN NOT NULL DEFAULT 1,
                            classified_at DATETIME DEFAULT CURRENT_TIMESTAMP
                        )
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        INSERT INTO catalog_opportunities (
                            id, raw_message_id, opportunity_type, tags_json, title, deadline,
                            description, requirements, application_url, source_channel_name,
                            message_link, is_active, classified_at
                        )
                        SELECT
                            id, raw_message_id, opportunity_type, tags_json, title, deadline,
                            description, requirements, application_url, source_channel_name,
                            message_link, is_active, classified_at
                        FROM catalog_opportunities_old
                        """
                    )
                )
                await conn.execute(text("DROP TABLE catalog_opportunities_old"))
                await conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_catalog_opportunities_raw_message_id "
                        "ON catalog_opportunities (raw_message_id)"
                    )
                )


async def ensure_subscription_columns() -> None:
    """Partner / tariff fields on users (Startify B2B)."""
    dialect = engine.dialect.name
    async with engine.begin() as conn:
        if dialect == "sqlite":
            result = await conn.execute(text("PRAGMA table_info(users)"))
            columns = {row[1] for row in result.fetchall()}
            specs = [
                ("partner_source", "TEXT"),
                ("partner_ref", "TEXT"),
                ("tariff_plan", "TEXT DEFAULT 'freemium'"),
                ("tariff_expires_at", "DATETIME"),
                ("kaspi_phone", "TEXT"),
            ]
            for name, ddl in specs:
                if name not in columns:
                    await conn.execute(text(f"ALTER TABLE users ADD COLUMN {name} {ddl}"))
        elif dialect == "postgresql":
            await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS partner_source VARCHAR(64)"))
            await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS partner_ref VARCHAR(128)"))
            await conn.execute(
                text(
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS tariff_plan "
                    "VARCHAR(32) NOT NULL DEFAULT 'freemium'"
                )
            )
            await conn.execute(
                text("ALTER TABLE users ADD COLUMN IF NOT EXISTS tariff_expires_at TIMESTAMPTZ")
            )
            await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS kaspi_phone VARCHAR(32)"))

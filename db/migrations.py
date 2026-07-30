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


async def ensure_google_auth_columns() -> None:
    """Google Sign-In fields on users."""
    dialect = engine.dialect.name
    async with engine.begin() as conn:
        if dialect == "sqlite":
            result = await conn.execute(text("PRAGMA table_info(users)"))
            columns = {row[1] for row in result.fetchall()}
            specs = [
                ("google_sub", "TEXT"),
                ("email", "TEXT"),
                ("display_name", "TEXT"),
            ]
            for name, ddl in specs:
                if name not in columns:
                    await conn.execute(text(f"ALTER TABLE users ADD COLUMN {name} {ddl}"))
            await conn.execute(
                text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_google_sub ON users (google_sub)")
            )
        elif dialect == "postgresql":
            await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS google_sub VARCHAR(255)"))
            await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(255)"))
            await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS display_name VARCHAR(255)"))
            await conn.execute(
                text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_google_sub ON users (google_sub)")
            )


async def ensure_web_auth_columns() -> None:
    dialect = engine.dialect.name
    async with engine.begin() as conn:
        if dialect == "sqlite":
            result = await conn.execute(text("PRAGMA table_info(users)"))
            columns = {row[1] for row in result.fetchall()}
            if "password_hash" not in columns:
                await conn.execute(text("ALTER TABLE users ADD COLUMN password_hash TEXT"))
        elif dialect == "postgresql":
            await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255)"))


async def ensure_team_profiles_table() -> None:
    dialect = engine.dialect.name
    async with engine.begin() as conn:
        if dialect == "sqlite":
            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS team_profiles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
                        mode VARCHAR(32) NOT NULL DEFAULT 'seeking_team',
                        display_name VARCHAR(20) NOT NULL DEFAULT 'Участник',
                        role VARCHAR(32) NOT NULL DEFAULT 'other',
                        city VARCHAR(32) NOT NULL DEFAULT 'online',
                        raw_prompt TEXT NOT NULL,
                        skills_json TEXT NOT NULL DEFAULT '[]',
                        telegram_contact VARCHAR(64),
                        is_active BOOLEAN NOT NULL DEFAULT 1,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
            )
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_team_profiles_role ON team_profiles (role)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_team_profiles_city ON team_profiles (city)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_team_profiles_active ON team_profiles (is_active)"))
        elif dialect == "postgresql":
            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS team_profiles (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
                        mode VARCHAR(32) NOT NULL DEFAULT 'seeking_team',
                        display_name VARCHAR(20) NOT NULL DEFAULT 'Участник',
                        role VARCHAR(32) NOT NULL DEFAULT 'other',
                        city VARCHAR(32) NOT NULL DEFAULT 'online',
                        raw_prompt TEXT NOT NULL,
                        skills_json TEXT NOT NULL DEFAULT '[]',
                        telegram_contact VARCHAR(64),
                        is_active BOOLEAN NOT NULL DEFAULT TRUE,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW()
                    )
                    """
                )
            )
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_team_profiles_role ON team_profiles (role)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_team_profiles_city ON team_profiles (city)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_team_profiles_active ON team_profiles (is_active)"))


async def ensure_mentor_workspace_tables() -> None:
    dialect = engine.dialect.name
    async with engine.begin() as conn:
        if dialect == "sqlite":
            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS mentor_applications (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        catalog_id INTEGER NOT NULL REFERENCES catalog_opportunities(id) ON DELETE CASCADE,
                        student_name VARCHAR(120) NOT NULL DEFAULT 'Студент',
                        status VARCHAR(32) NOT NULL DEFAULT 'todo',
                        notes TEXT,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, catalog_id, student_name)
                    )
                    """
                )
            )
            await conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_mentor_app_user ON mentor_applications (user_id)")
            )
            await conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_mentor_app_status ON mentor_applications (status)")
            )
            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS mentor_shortlists (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        title VARCHAR(200) NOT NULL,
                        agency_name VARCHAR(120) NOT NULL DEFAULT 'Lumo',
                        slug VARCHAR(16) NOT NULL UNIQUE,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
            )
            await conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_mentor_shortlist_user ON mentor_shortlists (user_id)")
            )
            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS mentor_shortlist_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        shortlist_id INTEGER NOT NULL REFERENCES mentor_shortlists(id) ON DELETE CASCADE,
                        catalog_id INTEGER NOT NULL REFERENCES catalog_opportunities(id) ON DELETE CASCADE,
                        sort_order INTEGER NOT NULL DEFAULT 0
                    )
                    """
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_mentor_shortlist_items ON mentor_shortlist_items (shortlist_id)"
                )
            )
        elif dialect == "postgresql":
            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS mentor_applications (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        catalog_id INTEGER NOT NULL REFERENCES catalog_opportunities(id) ON DELETE CASCADE,
                        student_name VARCHAR(120) NOT NULL DEFAULT 'Студент',
                        status VARCHAR(32) NOT NULL DEFAULT 'todo',
                        notes TEXT,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW(),
                        CONSTRAINT uq_mentor_app_student_catalog UNIQUE (user_id, catalog_id, student_name)
                    )
                    """
                )
            )
            await conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_mentor_app_user ON mentor_applications (user_id)")
            )
            await conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_mentor_app_status ON mentor_applications (status)")
            )
            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS mentor_shortlists (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        title VARCHAR(200) NOT NULL,
                        agency_name VARCHAR(120) NOT NULL DEFAULT 'Lumo',
                        slug VARCHAR(16) NOT NULL UNIQUE,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                    """
                )
            )
            await conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_mentor_shortlist_user ON mentor_shortlists (user_id)")
            )
            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS mentor_shortlist_items (
                        id SERIAL PRIMARY KEY,
                        shortlist_id INTEGER NOT NULL REFERENCES mentor_shortlists(id) ON DELETE CASCADE,
                        catalog_id INTEGER NOT NULL REFERENCES catalog_opportunities(id) ON DELETE CASCADE,
                        sort_order INTEGER NOT NULL DEFAULT 0
                    )
                    """
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_mentor_shortlist_items ON mentor_shortlist_items (shortlist_id)"
                )
            )


async def ensure_catalog_country_column() -> None:
    """Target country / audience geo on catalog_opportunities."""
    dialect = engine.dialect.name
    async with engine.begin() as conn:
        if dialect == "sqlite":
            result = await conn.execute(text("PRAGMA table_info(catalog_opportunities)"))
            columns = {row[1] for row in result.fetchall()}
            if "country" not in columns:
                await conn.execute(text("ALTER TABLE catalog_opportunities ADD COLUMN country TEXT"))
        elif dialect == "postgresql":
            await conn.execute(
                text("ALTER TABLE catalog_opportunities ADD COLUMN IF NOT EXISTS country VARCHAR(64)")
            )


async def ensure_user_role_column() -> None:
    dialect = engine.dialect.name
    async with engine.begin() as conn:
        if dialect == "sqlite":
            result = await conn.execute(text("PRAGMA table_info(users)"))
            columns = {row[1] for row in result.fetchall()}
            if "role" not in columns:
                await conn.execute(
                    text("ALTER TABLE users ADD COLUMN role VARCHAR(16) NOT NULL DEFAULT 'student'")
                )
        elif dialect == "postgresql":
            await conn.execute(
                text("ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(16) NOT NULL DEFAULT 'student'")
            )


async def ensure_student_profile_columns() -> None:
    """Класс / регион / уровень английского / предметы — структурированный профиль ученика."""
    dialect = engine.dialect.name
    async with engine.begin() as conn:
        if dialect == "sqlite":
            result = await conn.execute(text("PRAGMA table_info(users)"))
            columns = {row[1] for row in result.fetchall()}
            specs = [
                ("grade", "VARCHAR(32)"),
                ("region", "VARCHAR(64)"),
                ("english_level", "VARCHAR(16)"),
                ("subjects_json", "TEXT"),
                ("visible_in_community", "BOOLEAN NOT NULL DEFAULT 0"),
            ]
            for name, ddl in specs:
                if name not in columns:
                    await conn.execute(text(f"ALTER TABLE users ADD COLUMN {name} {ddl}"))
        elif dialect == "postgresql":
            await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS grade VARCHAR(32)"))
            await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS region VARCHAR(64)"))
            await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS english_level VARCHAR(16)"))
            await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS subjects_json TEXT"))
            await conn.execute(
                text(
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS visible_in_community "
                    "BOOLEAN NOT NULL DEFAULT FALSE"
                )
            )
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_region ON users (region)"))


async def ensure_catalog_ai_brief_columns() -> None:
    """AI-саммари в буллетах + чеклист требований — кэш на карточке конкурса."""
    dialect = engine.dialect.name
    async with engine.begin() as conn:
        if dialect == "sqlite":
            result = await conn.execute(text("PRAGMA table_info(catalog_opportunities)"))
            columns = {row[1] for row in result.fetchall()}
            if "ai_summary_json" not in columns:
                await conn.execute(text("ALTER TABLE catalog_opportunities ADD COLUMN ai_summary_json TEXT"))
            if "requirements_checklist_json" not in columns:
                await conn.execute(
                    text("ALTER TABLE catalog_opportunities ADD COLUMN requirements_checklist_json TEXT")
                )
        elif dialect == "postgresql":
            await conn.execute(
                text("ALTER TABLE catalog_opportunities ADD COLUMN IF NOT EXISTS ai_summary_json TEXT")
            )
            await conn.execute(
                text(
                    "ALTER TABLE catalog_opportunities ADD COLUMN IF NOT EXISTS "
                    "requirements_checklist_json TEXT"
                )
            )


async def ensure_shared_rooms_tables() -> None:
    dialect = engine.dialect.name
    await ensure_user_role_column()
    async with engine.begin() as conn:
        if dialect == "sqlite":
            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS shared_rooms (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        student_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
                        mentor_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                        invite_token VARCHAR(64) NOT NULL UNIQUE,
                        pending_mentor_email VARCHAR(255),
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
            )
            await conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_shared_rooms_mentor ON shared_rooms (mentor_id)")
            )
            result = await conn.execute(text("PRAGMA table_info(mentor_applications)"))
            columns = {row[1] for row in result.fetchall()}
            if "student_user_id" not in columns:
                await conn.execute(
                    text("ALTER TABLE mentor_applications ADD COLUMN student_user_id INTEGER REFERENCES users(id)")
                )
                await conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_mentor_app_student_user "
                        "ON mentor_applications (student_user_id)"
                    )
                )
        elif dialect == "postgresql":
            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS shared_rooms (
                        id SERIAL PRIMARY KEY,
                        student_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
                        mentor_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                        invite_token VARCHAR(64) NOT NULL UNIQUE,
                        pending_mentor_email VARCHAR(255),
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                    """
                )
            )
            await conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_shared_rooms_mentor ON shared_rooms (mentor_id)")
            )
            await conn.execute(
                text(
                    "ALTER TABLE mentor_applications "
                    "ADD COLUMN IF NOT EXISTS student_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_mentor_app_student_user "
                    "ON mentor_applications (student_user_id)"
                )
            )


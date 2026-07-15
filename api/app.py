import asyncio
import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from api.routes import admin, admin_tracking, catalog, grants, leads, lumo, partner, rooms, submissions, team_finder, traction, web_auth, workspace
from config import BASE_DIR, get_settings
from db.base import Base, async_session_factory, configure_supabase_pooler, engine
from scripts.seed_catalog import seed_catalog_if_empty
from services.opportunity_catalog import catalog_repo

logger = logging.getLogger(__name__)


async def _api_startup_maintenance() -> None:
    """Не блокирует /api/health — main.py делает то же при старте через init_database()."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        from db.migrations import (
            ensure_catalog_country_column,
            ensure_catalog_multi_per_message,
            ensure_google_auth_columns,
            ensure_subscription_columns,
            ensure_team_profiles_table,
            ensure_mentor_workspace_tables,
            ensure_shared_rooms_tables,
            ensure_web_auth_columns,
        )

        await ensure_catalog_multi_per_message()
        await ensure_catalog_country_column()
        await ensure_subscription_columns()
        await ensure_google_auth_columns()
        await ensure_web_auth_columns()
        await ensure_team_profiles_table()
        await ensure_mentor_workspace_tables()
        await ensure_shared_rooms_tables()

        async with async_session_factory() as session:
            await seed_catalog_if_empty(session)
            repo = catalog_repo(session)
            await repo.archive_stale_unclassified(limit=200)
            expired_ids = await repo.deactivate_expired()
            stale_ids = await repo.deactivate_stale_without_deadline()
            old_ids = await repo.deactivate_old_posts()
            await session.commit()
            deactivated_ids = list(dict.fromkeys([*expired_ids, *stale_ids, *old_ids]))
            if deactivated_ids:
                from services.startify_catalog_push import schedule_catalog_deactivate

                schedule_catalog_deactivate(deactivated_ids)
        logger.info("API startup maintenance finished")
    except Exception as exc:
        logger.warning("API startup maintenance: %s", exc)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        await configure_supabase_pooler()
    except Exception as exc:
        logger.warning("Supabase pooler probe: %s", exc)
    asyncio.create_task(_api_startup_maintenance())
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="AI Startify Grants API",
        description="Backend for the grants showcase from @opportunities_zula",
        version="1.0.0",
        lifespan=lifespan,
    )

    origins = [o.strip().rstrip("/") for o in settings.api_cors_origins.split(",") if o.strip()]
    cors_kwargs: dict = {
        "allow_methods": ["*"],
        "allow_headers": ["*"],
        "allow_origin_regex": r"https://([a-z0-9-]+\.)*vercel\.app",
    }
    if origins:
        cors_kwargs["allow_origins"] = origins
        cors_kwargs["allow_credentials"] = True
    else:
        cors_kwargs["allow_origins"] = ["*"]
        cors_kwargs["allow_credentials"] = False

    app.add_middleware(CORSMiddleware, **cors_kwargs)

    app.include_router(grants.router, prefix="/api")
    app.include_router(catalog.router, prefix="/api")
    app.include_router(leads.router, prefix="/api")
    app.include_router(admin.router, prefix="/api")
    app.include_router(admin_tracking.router, prefix="/api")
    app.include_router(lumo.router, prefix="/api")
    app.include_router(team_finder.router, prefix="/api")
    app.include_router(workspace.router, prefix="/api")
    app.include_router(rooms.router, prefix="/api")
    app.include_router(submissions.router, prefix="/api")
    app.include_router(traction.router, prefix="/api")
    app.include_router(web_auth.router, prefix="/api")
    app.include_router(partner.router, prefix="/api")

    @app.get("/api/health")
    async def health() -> dict:
        payload: dict = {"status": "ok"}
        try:
            from sqlalchemy import text

            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            payload["db"] = "ok"
        except Exception as exc:
            payload["db"] = "error"
            payload["dbError"] = type(exc).__name__
            logger.warning("Health DB check failed: %s", exc)
        return payload

    @app.get("/")
    async def root() -> RedirectResponse:
        if settings.serve_mini_app:
            mini_app_dist = BASE_DIR / "telegram-site" / "frontend" / "dist"
            if mini_app_dist.is_dir():
                return RedirectResponse(url="/app/", status_code=302)
        return RedirectResponse(url="/api/health", status_code=302)

    if settings.serve_mini_app:
        mini_app_dist = BASE_DIR / "telegram-site" / "frontend" / "dist"
        if mini_app_dist.is_dir():
            app.mount("/app", StaticFiles(directory=mini_app_dist, html=True), name="mini-app")

    return app


app = create_app()

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from api.routes import admin, admin_tracking, catalog, grants, leads, lumo, partner, submissions, traction
from config import BASE_DIR, get_settings
from db.base import Base, async_session_factory, engine
from scripts.seed_catalog import seed_catalog_if_empty
from services.opportunity_catalog import catalog_repo


@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from db.base import async_session_factory
    from db.migrations import ensure_catalog_multi_per_message, ensure_subscription_columns

    await ensure_catalog_multi_per_message()
    await ensure_subscription_columns()

    async with async_session_factory() as session:
        await seed_catalog_if_empty(session)
        repo = catalog_repo(session)
        await repo.archive_stale_unclassified(limit=200)
        await repo.deactivate_expired()
        await repo.deactivate_stale_without_deadline()
        await repo.deactivate_old_posts()
        await session.commit()
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
    app.include_router(submissions.router, prefix="/api")
    app.include_router(traction.router, prefix="/api")
    app.include_router(partner.router, prefix="/api")

    @app.get("/api/health")
    async def health() -> dict:
        return {"status": "ok"}

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

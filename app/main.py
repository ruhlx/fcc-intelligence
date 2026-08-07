"""FastAPI application entry point (Stage 7)."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import companies, contacts, discover, filings, ingest, search
from app.config import get_settings
from app.logging_config import configure_logging, get_logger

# Built SPA — served by the API when present, so `uvicorn app.main:app` runs the
# whole app locally as a single process.
_FRONTEND_DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"


def create_app() -> FastAPI:
    """Application factory — configures logging and registers routers."""
    settings = get_settings()
    configure_logging(level=settings.log_level, fmt=settings.log_format)
    logger = get_logger(__name__)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        # Apply migrations on boot when enabled (free-tier deploys have no
        # pre-deploy hook). Failures are logged but don't block startup, so
        # /health and /docs stay reachable for debugging.
        if settings.auto_migrate:
            from app.db.migrate import run_migrations

            try:
                run_migrations()
            except Exception as exc:  # broad: never crash boot on migration error
                logger.error("auto_migrate_failed", error=str(exc))

        # Optional in-process scheduler: periodically discover new filings
        # (by date range + region) without anyone naming a company. Only runs
        # while this process is alive — see start_auto_discover_loop().
        auto_discover_task: asyncio.Task[None] | None = None
        if settings.auto_discover_interval_hours > 0:
            from app.services.jobs import start_auto_discover_loop

            auto_discover_task = start_auto_discover_loop(
                settings.auto_discover_interval_hours
            )
            logger.info(
                "auto_discover_scheduled",
                interval_hours=settings.auto_discover_interval_hours,
                regions=settings.discover_regions,
            )

        yield

        if auto_discover_task is not None:
            auto_discover_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await auto_discover_task

    app = FastAPI(
        title="FCC Regulatory Contact Intelligence Platform",
        version="0.1.0",
        summary="Searchable database of product-compliance contacts from FCC filings.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    app.include_router(companies.router)
    app.include_router(contacts.router)
    app.include_router(filings.router)
    app.include_router(search.router)
    app.include_router(ingest.router)
    app.include_router(discover.router)

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        """Liveness probe."""
        return {"status": "ok"}

    # Mount the SPA last so API routes take precedence; falls back to /docs when
    # the frontend hasn't been built (e.g. the API-only cloud deploy).
    if _FRONTEND_DIST.is_dir():
        app.mount("/", StaticFiles(directory=_FRONTEND_DIST, html=True), name="ui")
        logger.info("serving_frontend", path=str(_FRONTEND_DIST))
    else:

        @app.get("/", include_in_schema=False)
        def root() -> RedirectResponse:
            """Send the bare URL to the interactive API docs."""
            return RedirectResponse(url="/docs")

    logger.info("app_started")
    return app


app = create_app()

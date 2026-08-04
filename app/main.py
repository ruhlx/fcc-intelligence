"""FastAPI application entry point (Stage 7)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api.routes import companies, contacts, filings, ingest, search
from app.config import get_settings
from app.logging_config import configure_logging, get_logger


def create_app() -> FastAPI:
    """Application factory — configures logging and registers routers."""
    settings = get_settings()
    configure_logging(level=settings.log_level, fmt=settings.log_format)
    logger = get_logger(__name__)

    app = FastAPI(
        title="FCC Regulatory Contact Intelligence Platform",
        version="0.1.0",
        summary="Searchable database of product-compliance contacts from FCC filings.",
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

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        """Send the bare URL to the interactive API docs."""
        return RedirectResponse(url="/docs")

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        """Liveness probe."""
        return {"status": "ok"}

    logger.info("app_started")
    return app


app = create_app()

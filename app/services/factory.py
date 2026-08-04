"""Factory helpers wiring pipeline dependencies together (dependency injection)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.crawler import FccClient
from app.extractor import ContactExtractor, build_extractor
from app.services.pipeline import IngestionPipeline


def build_pipeline(
    session: Session,
    *,
    settings: Settings | None = None,
    client: FccClient | None = None,
    extractor: ContactExtractor | None = None,
) -> IngestionPipeline:
    """Construct an :class:`IngestionPipeline` with sensible production defaults.

    Any collaborator can be overridden (e.g. with a fake) for testing.
    """
    settings = settings or get_settings()
    settings.ensure_directories()
    return IngestionPipeline(
        session,
        client=client or FccClient(settings),
        extractor=extractor or build_extractor(settings),
        settings=settings,
    )

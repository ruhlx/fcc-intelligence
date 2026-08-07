"""Shared response model + auth check for the ingest/discover job endpoints."""

from __future__ import annotations

from fastapi import HTTPException
from pydantic import BaseModel

from app.config import get_settings


class JobOut(BaseModel):
    """Job status response (shared shape for ingest and discovery jobs)."""

    id: str
    company: str
    status: str
    created_at: str
    report: dict[str, object] | None = None
    error: str | None = None


def check_ingest_token(token: str | None) -> None:
    """Raise 401 when ``INGEST_TOKEN`` is configured and doesn't match."""
    configured = get_settings().ingest_token
    if configured and token != configured:
        raise HTTPException(status_code=401, detail="Invalid or missing ingest token")

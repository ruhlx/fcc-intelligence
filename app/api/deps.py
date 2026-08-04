"""Shared FastAPI dependencies."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.db.session import get_db


def db_session() -> Iterator[Session]:
    """Yield a request-scoped SQLAlchemy session."""
    yield from get_db()

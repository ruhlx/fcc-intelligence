"""Database engine / session management."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings


def make_engine(url: str) -> Engine:
    """Build an engine for ``url``, tuning SQLite for concurrent crawl + serve.

    File-based SQLite uses WAL journalling + a busy timeout so a running crawl
    (writer) and the API (readers) don't deadlock with "database is locked".
    In-memory SQLite keeps a single shared connection so the data persists.
    """
    if not url.startswith("sqlite"):
        return create_engine(url, pool_pre_ping=True, future=True)

    in_memory = url == "sqlite://" or ":memory:" in url
    kwargs: dict[str, object] = {
        "future": True,
        "connect_args": {"check_same_thread": False},
    }
    if in_memory:
        kwargs["poolclass"] = StaticPool
    engine = create_engine(url, **kwargs)

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn: object, _rec: object) -> None:
        cur = dbapi_conn.cursor()  # type: ignore[attr-defined]
        if not in_memory:
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA synchronous=NORMAL")
        cur.execute("PRAGMA busy_timeout=15000")
        cur.close()

    return engine


@lru_cache
def get_engine() -> Engine:
    """Return a process-wide SQLAlchemy engine built from settings."""
    return make_engine(get_settings().database_url)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    """Return a cached session factory bound to the engine."""
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional scope around a series of operations."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Iterator[Session]:
    """FastAPI dependency that yields a request-scoped session."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()

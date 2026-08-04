"""Shared pytest fixtures.

Tests run against an in-memory SQLite database so they need no external
services. SQLAlchemy renders the enum columns as ``VARCHAR`` and ``ilike`` as
``lower() LIKE lower()`` on SQLite, so the same models and queries exercise the
real code paths.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base, Company, Filing


@pytest.fixture
def engine() -> Iterator[Engine]:
    # StaticPool + check_same_thread=False keeps a single in-memory connection
    # that FastAPI's TestClient (which runs in a worker thread) can also use.
    eng = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    db = factory()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def company(session: Session) -> Company:
    obj = Company(name="u-blox", country="Switzerland", website="https://u-blox.com")
    session.add(obj)
    session.flush()
    return obj


@pytest.fixture
def filing(session: Session, company: Company) -> Filing:
    obj = Filing(
        company_id=company.id,
        fcc_id="XPYNORA-1",
        product_name="GNSS module",
        filing_date=date(2025, 1, 15),
    )
    session.add(obj)
    session.flush()
    return obj

"""Tests for the DB session helpers (session_scope / get_db)."""

from __future__ import annotations

import app.db.session as session_module
from app.models import Company


def test_session_scope_commits(engine, monkeypatch) -> None:
    from sqlalchemy.orm import sessionmaker

    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(session_module, "get_session_factory", lambda: factory)

    with session_module.session_scope() as db:
        db.add(Company(name="Acme"))

    with session_module.session_scope() as db:
        assert db.query(Company).filter_by(name="Acme").count() == 1


def test_session_scope_rolls_back(engine, monkeypatch) -> None:
    from sqlalchemy.orm import sessionmaker

    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(session_module, "get_session_factory", lambda: factory)

    class Boom(Exception):
        pass

    try:
        with session_module.session_scope() as db:
            db.add(Company(name="Ghost"))
            db.flush()
            raise Boom()
    except Boom:
        pass

    with session_module.session_scope() as db:
        assert db.query(Company).filter_by(name="Ghost").count() == 0


def test_get_db_yields_and_closes(engine, monkeypatch) -> None:
    from sqlalchemy.orm import sessionmaker

    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(session_module, "get_session_factory", lambda: factory)

    gen = session_module.get_db()
    db = next(gen)
    db.add(Company(name="Temp"))
    db.flush()
    gen.close()  # triggers the finally: session.close()

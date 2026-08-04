"""Tests for startup auto-migration (free-tier friendly schema creation)."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, inspect

from app.config import Settings

EXPECTED_TABLES = {
    "companies",
    "filings",
    "documents",
    "contacts",
    "contact_filings",
    "alembic_version",
}


def test_auto_migrate_defaults_false() -> None:
    assert Settings().auto_migrate is False


def test_run_migrations_invokes_alembic(monkeypatch) -> None:
    import app.db.migrate as migrate

    captured: dict[str, str] = {}
    monkeypatch.setattr(
        migrate.command, "upgrade", lambda cfg, rev: captured.update(rev=rev)
    )
    migrate.run_migrations()
    assert captured["rev"] == "head"


def test_run_migrations_creates_full_schema(monkeypatch, tmp_path: Path) -> None:
    # Point the Alembic env (which reads app settings) at a temp SQLite DB and
    # run the real migration end to end.
    db_path = tmp_path / "migrated.db"
    url = f"sqlite:///{db_path}"
    monkeypatch.setattr("app.config.get_settings", lambda: Settings(database_url=url))

    from app.db.migrate import run_migrations

    run_migrations()

    engine = create_engine(url)
    tables = set(inspect(engine).get_table_names())
    assert tables >= EXPECTED_TABLES

"""Programmatic Alembic migration runner.

Used to apply migrations at application startup so no separate (paid) pre-deploy
step is needed on hosts like Render's free tier. ``alembic upgrade head`` is
idempotent, so running it on every boot is safe.
"""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from app.logging_config import get_logger

logger = get_logger(__name__)

# repo root: app/db/migrate.py -> app/db -> app -> <root>
_ROOT = Path(__file__).resolve().parents[2]


def _alembic_config() -> Config:
    cfg = Config(str(_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_ROOT / "alembic"))
    return cfg


def run_migrations() -> None:
    """Upgrade the database to the latest revision.

    The DB URL is resolved inside ``alembic/env.py`` from application settings,
    so it always matches the running app's ``DATABASE_URL``.
    """
    logger.info("auto_migrate_start")
    command.upgrade(_alembic_config(), "head")
    logger.info("auto_migrate_done")

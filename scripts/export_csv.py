"""CLI: export the contacts database to ``contacts.csv`` (Stage 8).

Usage:
    poetry run python -m scripts.export_csv --out contacts.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

from app.config import get_settings
from app.db.session import session_scope
from app.logging_config import configure_logging, get_logger
from app.services.export_service import ExportService

logger = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export contacts to CSV.")
    parser.add_argument("--out", default="contacts.csv", help="Output CSV path.")
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(level=settings.log_level, fmt=settings.log_format)

    with session_scope() as session:
        path = ExportService(session).write_csv(Path(args.out))
    logger.info("exported", path=str(path))
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()

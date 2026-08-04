"""CLI: run the ingestion pipeline for one or more company names.

Usage:
    poetry run python -m scripts.run_pipeline u-blox "Nordic Semiconductor"
"""

from __future__ import annotations

import argparse
import asyncio

from app.config import get_settings
from app.db.session import session_scope
from app.logging_config import configure_logging, get_logger
from app.services.factory import build_pipeline

logger = get_logger(__name__)


async def _run(company_names: list[str]) -> None:
    settings = get_settings()
    for name in company_names:
        with session_scope() as session:
            pipeline = build_pipeline(session, settings=settings)
            report = await pipeline.run(name)
            logger.info(
                "run_complete",
                company=report.company,
                applications=report.applications,
                documents=report.documents,
                created=report.contacts_created,
                merged=report.contacts_merged,
                errors=len(report.errors),
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run FCC contact ingestion pipeline.")
    parser.add_argument("companies", nargs="+", help="Company / applicant names.")
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(level=settings.log_level, fmt=settings.log_format)
    asyncio.run(_run(args.companies))


if __name__ == "__main__":
    main()

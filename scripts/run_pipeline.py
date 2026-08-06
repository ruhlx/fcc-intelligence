"""CLI: run the ingestion pipeline for one or more company names.

By default only structured, freely-available contacts are collected (the 731
Responsible Party) — fast and no LLM. Pass ``--pdfs`` to also download and
LLM-mine the exhibit PDFs (needs an LLM key / quota).

Usage:
    python -m scripts.run_pipeline u-blox "Nordic Semiconductor"
    python -m scripts.run_pipeline --pdfs u-blox
"""

from __future__ import annotations

import argparse
import asyncio

from app.config import get_settings
from app.db.session import session_scope
from app.logging_config import configure_logging, get_logger
from app.services.factory import build_pipeline

logger = get_logger(__name__)


async def _run(company_names: list[str], *, extract_pdfs: bool) -> None:
    settings = get_settings()
    if extract_pdfs:
        settings = settings.model_copy(update={"extract_pdfs": True})
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
    parser.add_argument(
        "--pdfs",
        action="store_true",
        help="Also download and LLM-mine exhibit PDFs (needs an LLM key/quota).",
    )
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(level=settings.log_level, fmt=settings.log_format)
    asyncio.run(_run(args.companies, extract_pdfs=args.pdfs))


if __name__ == "__main__":
    main()

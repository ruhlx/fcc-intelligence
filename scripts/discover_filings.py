"""CLI: discover FCC filings/contacts by date range instead of company name.

Searches with a blank applicant name over a grant-date window and (by default)
keeps only European filings, so you don't have to think of client names —
this is how new companies/contacts get found automatically.

Usage:
    python -m scripts.discover_filings                  # last 3 days, Europe
    python -m scripts.discover_filings --days 7
    python -m scripts.discover_filings --regions all --pdfs
"""

from __future__ import annotations

import argparse
import asyncio

from app.config import get_settings
from app.db.session import session_scope
from app.logging_config import configure_logging, get_logger
from app.services.factory import build_pipeline

logger = get_logger(__name__)


async def _run(
    *, days: int | None, regions: str | None, extract_pdfs: bool, limit: int | None
) -> None:
    settings = get_settings()
    updates: dict[str, object] = {}
    if extract_pdfs:
        updates["extract_pdfs"] = True
    if days:
        updates["discover_days"] = days
    if updates:
        settings = settings.model_copy(update=updates)

    with session_scope() as session:
        pipeline = build_pipeline(session, settings=settings)
        report = await pipeline.run_discovery(regions=regions, max_filings=limit)
        logger.info(
            "discovery_complete",
            date_from=str(report.date_from),
            date_to=str(report.date_to),
            regions=report.regions,
            filings_scanned=report.filings_scanned,
            companies_touched=report.companies_touched,
            contacts_created=report.contacts_created,
            contacts_merged=report.contacts_merged,
            errors=len(report.errors),
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Discover FCC filings/contacts by date range (no company name needed)."
    )
    parser.add_argument(
        "--days", type=int, default=None, help="Lookback window in days (default: config)."
    )
    parser.add_argument(
        "--regions",
        default=None,
        help="'europe' (default), 'all', or a comma-separated FCC country list.",
    )
    parser.add_argument(
        "--pdfs",
        action="store_true",
        help="Also download and LLM-mine exhibit PDFs (needs an LLM key/quota).",
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Cap matching filings processed."
    )
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(level=settings.log_level, fmt=settings.log_format)
    asyncio.run(
        _run(days=args.days, regions=args.regions, extract_pdfs=args.pdfs, limit=args.limit)
    )


if __name__ == "__main__":
    main()

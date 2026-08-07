"""Stage 1 — look up FCC filings by applicant name or by date-range discovery."""

from __future__ import annotations

from datetime import date

from app.crawler.browser_fetcher import FccFetcher
from app.crawler.parsing import ApplicationRow, parse_search_results
from app.logging_config import get_logger

logger = get_logger(__name__)


class CompanyLookup:
    """Searches the EAS by applicant (grantee) name via a browser fetcher."""

    def __init__(self, fetcher: FccFetcher) -> None:
        self._fetcher = fetcher

    async def find_applications(
        self, company_name: str, *, show_records: int = 10
    ) -> list[ApplicationRow]:
        """Return every application row EAS lists for ``company_name``.

        :param company_name: Applicant/grantee name, e.g. ``"u-blox"``.
        :param show_records: How many result records to request (page size);
            large values pull all filings in one page.
        :returns: A list of :class:`ApplicationRow`, deduplicated by FCC ID.
        """
        logger.info("company_lookup_start", company=company_name)
        html = await self._fetcher.search(company_name, show_records=show_records)
        rows = parse_search_results(
            html, base_url=f"{self._fetcher.base_url}/GenericSearchResult.cfm"
        )
        logger.info("company_lookup_done", company=company_name, applications=len(rows))
        return rows

    async def find_recent_filings(
        self,
        date_from: date,
        date_to: date,
        *,
        show_records: int = 200,
        countries: frozenset[str] | None = None,
    ) -> list[ApplicationRow]:
        """Discover filings across *all* applicants within a grant-date window.

        No company name is required — this is how new companies get found
        instead of naming them up front. When ``countries`` is given, only
        rows whose parsed country is in that set are returned.
        """
        logger.info("discovery_start", date_from=str(date_from), date_to=str(date_to))
        html = await self._fetcher.search_by_date_range(
            date_from, date_to, show_records=show_records
        )
        rows = parse_search_results(
            html, base_url=f"{self._fetcher.base_url}/GenericSearchResult.cfm"
        )
        if countries is not None:
            rows = [r for r in rows if r.country in countries]
        logger.info(
            "discovery_done",
            date_from=str(date_from),
            date_to=str(date_to),
            filings=len(rows),
        )
        return rows

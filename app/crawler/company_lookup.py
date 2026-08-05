"""Stage 1 — look up all FCC IDs associated with an applicant/company name."""

from __future__ import annotations

from app.crawler.browser_fetcher import FccFetcher
from app.crawler.parsing import ApplicationRow, parse_search_results
from app.logging_config import get_logger

logger = get_logger(__name__)


class CompanyLookup:
    """Searches the EAS by applicant (grantee) name via a browser fetcher."""

    def __init__(self, fetcher: FccFetcher) -> None:
        self._fetcher = fetcher

    async def find_applications(self, company_name: str) -> list[ApplicationRow]:
        """Return every application row EAS lists for ``company_name``.

        :param company_name: Applicant/grantee name, e.g. ``"u-blox"``.
        :returns: A list of :class:`ApplicationRow`, deduplicated by FCC ID.
        """
        logger.info("company_lookup_start", company=company_name)
        html = await self._fetcher.search(company_name)
        rows = parse_search_results(
            html, base_url=f"{self._fetcher.base_url}/GenericSearchResult.cfm"
        )
        logger.info("company_lookup_done", company=company_name, applications=len(rows))
        return rows

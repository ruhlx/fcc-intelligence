"""Stage 1 — look up all FCC IDs associated with an applicant/company name."""

from __future__ import annotations

from app.crawler.fcc_client import FccClient
from app.crawler.parsing import ApplicationRow, parse_search_results
from app.logging_config import get_logger

logger = get_logger(__name__)


class CompanyLookup:
    """Searches the EAS Generic Search by grantee (applicant) name."""

    def __init__(self, client: FccClient) -> None:
        self._client = client

    async def find_applications(self, company_name: str) -> list[ApplicationRow]:
        """Return every application row EAS lists for ``company_name``.

        :param company_name: Applicant/grantee name, e.g. ``"u-blox"``.
        :returns: A list of :class:`ApplicationRow`, deduplicated by FCC ID.
        """
        url = f"{self._client.base_url}/GenericSearchResult.cfm"
        params = {
            "RequestTimeout": "500",
            "calledFromFrame": "N",
            "grantee_name": company_name,
        }
        logger.info("company_lookup_start", company=company_name)
        html = await self._client.get_html(url, params=params)
        rows = parse_search_results(html, base_url=url)
        logger.info(
            "company_lookup_done", company=company_name, applications=len(rows)
        )
        return rows

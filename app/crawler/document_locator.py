"""Stage 2 — locate and download the exhibits attached to an application."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.crawler.browser_fetcher import FccFetcher
from app.crawler.parsing import ApplicationRow, ExhibitRow, parse_exhibit_list
from app.logging_config import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class DownloadedExhibit:
    """An exhibit that has been fetched and written to local storage."""

    exhibit: ExhibitRow
    local_path: Path
    content: bytes


class DocumentLocator:
    """Finds exhibits for an application and downloads their PDFs."""

    def __init__(self, fetcher: FccFetcher, *, pdf_directory: Path) -> None:
        self._fetcher = fetcher
        self._pdf_directory = pdf_directory

    async def list_exhibits(self, app: ApplicationRow) -> list[ExhibitRow]:
        """Return the exhibit list for a single application.

        ``app.detail_url`` is the "Display Exhibits" page URL captured during
        the search, so we can fetch it directly.
        """
        url = app.detail_url or f"{self._fetcher.base_url}/ViewExhibitReport.cfm"
        html = await self._fetcher.get_html(url)
        exhibits = parse_exhibit_list(html, base_url=url)
        logger.info("exhibits_found", fcc_id=app.fcc_id, count=len(exhibits))
        return exhibits

    async def download_exhibit(
        self, fcc_id: str, exhibit: ExhibitRow, *, referer: str | None = None
    ) -> DownloadedExhibit:
        """Download a single exhibit PDF and persist it locally (Stage 2).

        ``referer`` should be the exhibit page URL — FCC/Akamai rejects
        attachment requests that don't carry it.
        """
        content = await self._fetcher.download(exhibit.pdf_url, referer=referer)
        local_path = self._target_path(fcc_id, exhibit)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(content)
        logger.info("exhibit_stored", fcc_id=fcc_id, path=str(local_path))
        return DownloadedExhibit(
            exhibit=exhibit, local_path=local_path, content=content
        )

    def _target_path(self, fcc_id: str, exhibit: ExhibitRow) -> Path:
        safe_fcc = _slug(fcc_id)
        filename = f"{_slug(exhibit.doc_type.value)}_{abs(hash(exhibit.pdf_url)) % 10**8}.pdf"
        return self._pdf_directory / safe_fcc / filename


def _slug(value: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in value)

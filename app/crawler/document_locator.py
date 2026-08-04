"""Stage 2 — locate and download the exhibits attached to an application."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.crawler.fcc_client import FccClient
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

    def __init__(self, client: FccClient, *, pdf_directory: Path) -> None:
        self._client = client
        self._pdf_directory = pdf_directory

    async def list_exhibits(self, app: ApplicationRow) -> list[ExhibitRow]:
        """Return the exhibit list for a single application."""
        url = f"{self._client.base_url}/ViewExhibitReport.cfm"
        params = {
            "mode": "Exhibits",
            "RequestTimeout": "500",
            "calledFromFrame": "N",
            "fcc_id": app.fcc_id,
        }
        if app.application_id:
            params["application_id"] = app.application_id
        html = await self._client.get_html(url, params=params)
        exhibits = parse_exhibit_list(html, base_url=url)
        logger.info("exhibits_found", fcc_id=app.fcc_id, count=len(exhibits))
        return exhibits

    async def download_exhibit(
        self, fcc_id: str, exhibit: ExhibitRow
    ) -> DownloadedExhibit:
        """Download a single exhibit PDF and persist it locally (Stage 2)."""
        content = await self._client.download(exhibit.pdf_url)
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

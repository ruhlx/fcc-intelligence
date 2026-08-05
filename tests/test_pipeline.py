"""End-to-end pipeline test with fake HTTP client, fake LLM, and patched OCR.

Exercises Stages 1-6 without any network access.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.orm import Session

import app.services.pipeline as pipeline_module
from app.config import Settings
from app.extractor.schemas import ExtractedContact, ExtractionResponse
from app.models import Company, Contact
from app.parser.pdf_extractor import ExtractionResult
from app.services.pipeline import IngestionPipeline

# Mirrors the real result page: one filing anchored on a Display-Exhibits link,
# with the applicant/country/date columns around the FCC-ID cell.
SEARCH_HTML = """
<table>
  <tr>
    <td></td>
    <td><a href="ViewExhibitReport.cfm?mode=Exhibits&application_id=1&fcc_id=XPYNORA-1">Ex</a></td>
    <td>Detail</td><td></td><td></td>
    <td>u-blox AG</td><td></td><td>Thalwil</td><td>N/A</td><td>Switzerland</td><td>CH-8800</td>
    <td>XPYNORA-1</td><td>Original Equipment</td><td>01/15/2025</td>
  </tr>
</table>
"""

EXHIBIT_HTML = """
<table>
  <tr><td>Cover Letter</td>
      <td><a href="GetApplicationAttachment.html?id=1">Download</a></td></tr>
</table>
"""


class FakeFetcher:
    def __init__(self, base_url: str = "https://apps.fcc.gov/oetcf/eas/reports") -> None:
        self.base_url = base_url
        self.downloads: list[str] = []
        self.closed = False

    async def search(self, company: str) -> str:
        return SEARCH_HTML

    async def get_html(self, url: str) -> str:
        return EXHIBIT_HTML

    async def download(self, url: str, *, referer: str | None = None) -> bytes:
        self.downloads.append(url)
        return b"%PDF-fake-bytes"

    async def aclose(self) -> None:
        self.closed = True


class FakeExtractor:
    def extract(self, *, document_text, document_type=None, company=None):
        return ExtractionResponse(
            contacts=[
                ExtractedContact(
                    full_name="Jane Doe",
                    email="jane@u-blox.com",
                    title="Certification Manager",
                    is_internal_employee=True,
                    confidence=92,
                ),
                ExtractedContact(
                    full_name="Ext Lawyer",
                    title="Attorney",
                    is_internal_employee=False,
                    confidence=70,
                ),
            ]
        )


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(data_directory=tmp_path, openai_api_key="test")


async def test_pipeline_run_end_to_end(session: Session, settings: Settings) -> None:
    settings.ensure_directories()
    # Real extract_text can't parse fake bytes; substitute rich text.
    def _fake_extract(data: bytes, *, enable_ocr: bool = True) -> ExtractionResult:
        return ExtractionResult(text="Signed by Jane Doe, Certification Manager", method="stub")

    pipeline_module.extract_text = _fake_extract  # type: ignore[assignment]

    fetcher = FakeFetcher()
    pipeline = IngestionPipeline(
        session,
        fetcher=fetcher,  # type: ignore[arg-type]
        extractor=FakeExtractor(),
        settings=settings,
    )
    report = await pipeline.run("u-blox")

    assert report.applications == 1
    assert report.documents == 1
    assert report.contacts_created == 1  # the external lawyer is dropped
    assert report.errors == []
    assert fetcher.closed  # pipeline releases the fetcher when done

    company = session.query(Company).filter_by(name="u-blox").one()
    contacts = session.query(Contact).filter_by(company_id=company.id).all()
    assert len(contacts) == 1
    assert contacts[0].full_name == "Jane Doe"
    assert contacts[0].priority == 50  # certification (40) + recent (10)
    assert {f.fcc_id for f in contacts[0].filings} == {"XPYNORA-1"}

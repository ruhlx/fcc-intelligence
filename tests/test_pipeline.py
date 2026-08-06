"""End-to-end pipeline tests with a fake fetcher and fake LLM (no network).

Covers the default mode (structured 731 Responsible Party only, no LLM) and the
opt-in deep mode (exhibit PDFs mined with the LLM).
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

# One filing, anchored on its Display-Exhibits link, plus the 731 "View Form" link.
SEARCH_HTML = """
<table>
  <tr>
    <td></td>
    <td><a href="/tcb/GetTcb731Report.do?applicationId=1&fcc_id=XPYNORA-1">Form</a></td>
    <td><a href="ViewExhibitReport.cfm?mode=Exhibits&application_id=1&fcc_id=XPYNORA-1">Ex</a></td>
    <td>Detail</td><td></td><td></td>
    <td>u-blox AG</td><td></td><td>Thalwil</td><td>N/A</td><td>Switzerland</td><td>CH-8800</td>
    <td>XPYNORA-1</td><td>Original Equipment</td><td>01/15/2025</td>
  </tr>
</table>
"""

# Minimal 731 form label/value table with a Responsible Party.
FORM_HTML = """
<table>
  <tr><td>First Name:</td><td>Jane</td></tr>
  <tr><td>Last Name:</td><td>Doe</td></tr>
  <tr><td>Title:</td><td>Certification Manager</td></tr>
  <tr><td>Telephone Number:</td><td>+41 44 000</td></tr>
  <tr><td>Email:</td><td>jane@u-blox.com</td></tr>
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
        return FORM_HTML if "GetTcb731Report" in url else EXHIBIT_HTML

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
                    full_name="Bob Cyber",
                    email="bob@u-blox.com",
                    title="Product Security Lead",
                    is_internal_employee=True,
                    confidence=88,
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


async def test_default_mode_form_only(session: Session, settings: Settings) -> None:
    """Default: only the structured 731 Responsible Party; no PDF/LLM work."""
    fetcher = FakeFetcher()
    pipeline = IngestionPipeline(
        session, fetcher=fetcher, extractor=FakeExtractor(), settings=settings  # type: ignore[arg-type]
    )
    report = await pipeline.run("u-blox")

    assert report.applications == 1
    assert report.contacts_created == 1  # Jane Doe from the form
    assert fetcher.downloads == []  # no exhibit PDFs downloaded
    company = session.query(Company).filter_by(name="u-blox").one()
    contact = session.query(Contact).filter_by(company_id=company.id).one()
    assert contact.full_name == "Jane Doe"
    assert contact.email == "jane@u-blox.com"
    assert contact.company.country == "Switzerland"
    assert fetcher.closed


async def test_deep_mode_extracts_pdfs(session: Session, settings: Settings) -> None:
    """--pdfs: also download and LLM-mine exhibit PDFs."""
    settings = settings.model_copy(update={"extract_pdfs": True})
    pipeline_module.extract_text = lambda data, enable_ocr=True: ExtractionResult(  # type: ignore[assignment]
        text="Signed by Bob Cyber, Product Security Lead", method="stub"
    )
    fetcher = FakeFetcher()
    pipeline = IngestionPipeline(
        session, fetcher=fetcher, extractor=FakeExtractor(), settings=settings  # type: ignore[arg-type]
    )
    await pipeline.run("u-blox")

    assert fetcher.downloads  # exhibit PDF was fetched
    names = {c.full_name for c in session.query(Contact).all()}
    assert "Jane Doe" in names  # from the form
    assert "Bob Cyber" in names  # from the exhibit LLM
    assert "Ext Lawyer" not in names  # external, dropped

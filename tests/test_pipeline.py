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

# One filing. Mirrors the REAL page's column layout (verified against
# tests/fixtures/fcc_search_result.html and ~60 live rows): the 731-form and
# grant/correspondence links are icon-only (no text), only the Exhibits link
# has visible text ("Detail Summary"), and the address-line cell is empty here.
SEARCH_HTML = """
<table>
  <tr>
    <td></td>
    <td><a href="/tcb/GetTcb731Report.do?applicationId=1&fcc_id=XPYNORA-1"></a></td>
    <td><a href="ViewExhibitReport.cfm?mode=Exhibits&application_id=1&fcc_id=XPYNORA-1">
      Detail Summary</a></td>
    <td><a href="Tcb731GrantForm.cfm?application_id=1&fcc_id=XPYNORA-1"></a></td>
    <td><a href="ViewCorrespondenceReport.cfm?application_id=1&fcc_id=XPYNORA-1"></a></td>
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

# Two filings for two DIFFERENT companies/countries — used by discovery-mode
# tests. The second row has a non-empty ADDRESS-LINE cell (like "Ameri Corp" /
# real "Intel Corporation" filings do) while the first doesn't (like "Euro
# Corp" / real "u-blox AG" filings) — this is the exact structural difference
# that broke applicant-name parsing for companies with a street-address line
# (see _row_fields' docstring). Both rows must still resolve the correct
# applicant despite the extra cell shifting everything after it.
DISCOVERY_HTML = """
<table>
  <tr>
    <td></td>
    <td><a href="/tcb/GetTcb731Report.do?applicationId=10&fcc_id=EUFIL001"></a></td>
    <td><a href="ViewExhibitReport.cfm?mode=Exhibits&application_id=10&fcc_id=EUFIL001">
      Detail Summary</a></td>
    <td><a href="Tcb731GrantForm.cfm?application_id=10&fcc_id=EUFIL001"></a></td>
    <td><a href="ViewCorrespondenceReport.cfm?application_id=10&fcc_id=EUFIL001"></a></td>
    <td>Euro Corp</td><td></td><td>Munich</td><td>N/A</td><td>Germany</td><td>80331</td>
    <td>EUFIL001</td><td>Original Equipment</td><td>01/15/2025</td>
  </tr>
  <tr>
    <td></td>
    <td><a href="/tcb/GetTcb731Report.do?applicationId=20&fcc_id=USFIL002"></a></td>
    <td><a href="ViewExhibitReport.cfm?mode=Exhibits&application_id=20&fcc_id=USFIL002">
      Detail Summary</a></td>
    <td><a href="Tcb731GrantForm.cfm?application_id=20&fcc_id=USFIL002"></a></td>
    <td><a href="ViewCorrespondenceReport.cfm?application_id=20&fcc_id=USFIL002"></a></td>
    <td>Ameri Corp</td><td>500 Main St</td><td>Austin</td><td>TX</td>
    <td>United States</td><td>78701</td>
    <td>USFIL002</td><td>Original Equipment</td><td>01/16/2025</td>
  </tr>
</table>
"""


class FakeFetcher:
    def __init__(self, base_url: str = "https://apps.fcc.gov/oetcf/eas/reports") -> None:
        self.base_url = base_url
        self.downloads: list[str] = []
        self.closed = False
        self.show_records = 0

    async def search(self, company: str, *, show_records: int = 10) -> str:
        self.show_records = show_records
        return SEARCH_HTML

    async def search_by_date_range(self, date_from, date_to, *, show_records: int = 200) -> str:
        self.show_records = show_records
        return DISCOVERY_HTML

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
    assert fetcher.show_records == 100  # structured mode default cap
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

    assert fetcher.show_records == 10  # deep mode stays capped
    assert fetcher.downloads  # exhibit PDF was fetched
    names = {c.full_name for c in session.query(Contact).all()}
    assert "Jane Doe" in names  # from the form
    assert "Bob Cyber" in names  # from the exhibit LLM
    assert "Ext Lawyer" not in names  # external, dropped


async def test_discovery_filters_to_europe(session: Session, settings: Settings) -> None:
    """run_discovery(regions='europe') keeps only the European filing."""
    fetcher = FakeFetcher()
    pipeline = IngestionPipeline(
        session, fetcher=fetcher, extractor=FakeExtractor(), settings=settings  # type: ignore[arg-type]
    )
    report = await pipeline.run_discovery(regions="europe")

    assert report.regions == "europe"
    assert report.filings_scanned == 1
    assert report.companies_touched == 1
    assert fetcher.closed

    euro = session.query(Company).filter_by(name="Euro Corp").one()
    assert euro.country == "Germany"
    assert session.query(Contact).filter_by(company_id=euro.id).one().full_name == "Jane Doe"
    assert session.query(Company).filter_by(name="Ameri Corp").first() is None


async def test_discovery_all_regions_processes_every_company(
    session: Session, settings: Settings
) -> None:
    fetcher = FakeFetcher()
    pipeline = IngestionPipeline(
        session, fetcher=fetcher, extractor=FakeExtractor(), settings=settings  # type: ignore[arg-type]
    )
    report = await pipeline.run_discovery(regions="all")

    assert report.filings_scanned == 2
    assert report.companies_touched == 2
    names = {c.name for c in session.query(Company).all()}
    assert {"Euro Corp", "Ameri Corp"} <= names
    # Regression guard: the address-line cell on "Ameri Corp"'s row must not
    # shift the applicant offset and get stored as the company name instead.
    assert "500 Main St" not in names


async def test_discovery_respects_max_filings(session: Session, settings: Settings) -> None:
    fetcher = FakeFetcher()
    pipeline = IngestionPipeline(
        session, fetcher=fetcher, extractor=FakeExtractor(), settings=settings  # type: ignore[arg-type]
    )
    report = await pipeline.run_discovery(regions="all", max_filings=1)

    assert report.filings_scanned == 1
    assert report.companies_touched == 1

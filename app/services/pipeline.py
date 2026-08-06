"""End-to-end ingestion pipeline (Stages 1-6, plus scoring).

Coordinates crawling, downloading, text extraction, LLM extraction and
persistence for one applicant. External collaborators (HTTP client, LLM
extractor, DB session) are injected so the pipeline can be tested in isolation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.crawler import ApplicationRow, CompanyLookup, DocumentLocator, FccFetcher
from app.crawler.parsing import parse_application_form
from app.db.repositories import (
    CompanyRepository,
    DocumentRepository,
    FilingRepository,
)
from app.extractor import ContactExtractor
from app.extractor.schemas import ExtractedContact
from app.logging_config import get_logger
from app.models import Filing
from app.models.enums import DocumentType
from app.parser import extract_text, html_to_text
from app.services.contact_service import ContactIngestionService

logger = get_logger(__name__)


@dataclass
class PipelineReport:
    """Aggregated results of a pipeline run for a company."""

    company: str
    applications: int = 0
    documents: int = 0
    contacts_created: int = 0
    contacts_merged: int = 0
    errors: list[str] = field(default_factory=list)


class IngestionPipeline:
    """Runs the full extraction pipeline for a single applicant name."""

    def __init__(
        self,
        session: Session,
        *,
        fetcher: FccFetcher,
        extractor: ContactExtractor,
        settings: Settings | None = None,
    ) -> None:
        self._session = session
        self._settings = settings or get_settings()
        self._fetcher = fetcher
        self._extractor = extractor
        self._lookup = CompanyLookup(fetcher)
        self._locator = DocumentLocator(fetcher, pdf_directory=self._settings.pdf_directory)
        self._companies = CompanyRepository(session)
        self._filings = FilingRepository(session)
        self._documents = DocumentRepository(session)
        self._ingestion = ContactIngestionService(session)

    async def run(self, company_name: str) -> PipelineReport:
        """Execute Stages 1-6 for ``company_name`` and persist the results."""
        report = PipelineReport(company=company_name)
        company = self._companies.get_or_create(company_name)
        self._session.flush()

        try:
            # Default (structured) mode is free, so pull all filings; deep mode
            # stays capped because each filing means many PDFs + LLM calls.
            cap = (
                self._settings.fcc_max_filings
                if self._settings.extract_pdfs
                else self._settings.fcc_max_filings_structured
            )
            applications = await self._lookup.find_applications(
                company_name, show_records=cap
            )
            applications = applications[:cap]
            report.applications = len(applications)

            # Backfill the company's country from the first filing's applicant row.
            if applications and applications[0].country and not company.country:
                company.country = applications[0].country

            for app in applications:
                try:
                    await self._process_application(company.id, app, report)
                except Exception as exc:  # broad: isolate per-application failures
                    logger.error("application_failed", fcc_id=app.fcc_id, error=str(exc))
                    report.errors.append(f"{app.fcc_id}: {exc}")

            self._session.commit()
        finally:
            await self._fetcher.aclose()

        logger.info(
            "pipeline_done",
            company=company_name,
            created=report.contacts_created,
            merged=report.contacts_merged,
        )
        return report

    async def _process_application(
        self, company_id: int, app: ApplicationRow, report: PipelineReport
    ) -> None:
        filing = self._filings.get_or_create(
            company_id=company_id,
            fcc_id=app.fcc_id,
            product_name=app.product_name,
            filing_date=app.filing_date,
            filing_url=app.detail_url,
        )
        # The 731 "View Form" page holds the structured Responsible Party
        # contact (name/title/email/phone) — always processed, no LLM needed.
        if app.form_url:
            await self._process_form(company_id, filing, app.form_url, report)

        # Deep mode (opt-in): also download and LLM-mine the exhibit PDFs.
        if self._settings.extract_pdfs:
            exhibits = await self._locator.list_exhibits(app)
            for exhibit in exhibits:
                await self._process_exhibit(
                    company_id, filing, exhibit, report, app.detail_url
                )

    async def _process_form(
        self, company_id: int, filing: Filing, form_url: str, report: PipelineReport
    ) -> None:
        """Parse the 731 form's Responsible Party structurally (no LLM needed)."""
        html = await self._fetcher.get_html(form_url)
        document = self._documents.get_or_create(
            filing_id=filing.id, pdf_url=form_url, doc_type=DocumentType.OTHER
        )
        document.parsed_text = html_to_text(html)
        report.documents += 1

        extracted = [
            ExtractedContact(
                full_name=fc.full_name,
                email=fc.email,
                phone=fc.phone,
                title=fc.title,
                is_internal_employee=True,
                confidence=85,
            )
            for fc in parse_application_form(html)
        ]
        if not extracted:
            return
        summary = self._ingestion.ingest(
            company_id=company_id,
            filing=filing,
            extracted=extracted,
            source_document=form_url,
        )
        report.contacts_created += summary.created
        report.contacts_merged += summary.merged

    async def _process_exhibit(
        self,
        company_id: int,
        filing: Filing,
        exhibit: object,
        report: PipelineReport,
        referer: str | None,
    ) -> None:
        downloaded = await self._locator.download_exhibit(
            filing.fcc_id, exhibit, referer=referer  # type: ignore[arg-type]
        )
        document = self._documents.get_or_create(
            filing_id=filing.id,
            pdf_url=downloaded.exhibit.pdf_url,
            doc_type=downloaded.exhibit.doc_type,
        )
        document.local_path = str(downloaded.local_path)
        report.documents += 1

        extraction = extract_text(downloaded.content)
        document.parsed_text = extraction.text
        if not extraction.text:
            logger.warning("no_text_extracted", fcc_id=filing.fcc_id)
            return

        self._extract_and_ingest(
            company_id,
            filing,
            extraction.text,
            downloaded.exhibit.doc_type.value,
            downloaded.exhibit.pdf_url,
            report,
        )

    def _extract_and_ingest(
        self,
        company_id: int,
        filing: Filing,
        text: str,
        doc_type_label: str,
        source: str,
        report: PipelineReport,
    ) -> None:
        response = self._extractor.extract(
            document_text=text,
            document_type=doc_type_label,
            company=filing.company.name if filing.company else None,
        )
        summary = self._ingestion.ingest(
            company_id=company_id,
            filing=filing,
            extracted=response.contacts,
            source_document=source,
        )
        report.contacts_created += summary.created
        report.contacts_merged += summary.merged

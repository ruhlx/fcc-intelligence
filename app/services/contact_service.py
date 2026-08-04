"""Ingestion service - turns LLM output into persisted, scored contacts.

Wires together Stage 5 (classification), Stage 6 (deduplication) and Stage 9
(priority scoring). Only saveable categories are persisted.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.repositories import ContactRepository
from app.enrichment.classification import classify_title, is_saveable
from app.enrichment.dedup import CandidateContact, ContactDeduplicator
from app.enrichment.priority import PriorityInput, compute_priority
from app.extractor.schemas import ExtractedContact
from app.logging_config import get_logger
from app.models import Filing

logger = get_logger(__name__)


@dataclass
class IngestSummary:
    """Counts describing the outcome of an ingestion run."""

    considered: int = 0
    skipped_external: int = 0
    skipped_category: int = 0
    created: int = 0
    merged: int = 0


class ContactIngestionService:
    """Persists extracted contacts for a filing."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = ContactRepository(session)
        self._dedup = ContactDeduplicator(self._repo)

    def ingest(
        self,
        *,
        company_id: int,
        filing: Filing,
        extracted: Iterable[ExtractedContact],
        source_document: str | None = None,
    ) -> IngestSummary:
        """Classify, filter, dedupe, score and store extracted contacts."""
        summary = IngestSummary()
        for item in extracted:
            summary.considered += 1

            if not item.is_internal_employee:
                summary.skipped_external += 1
                logger.debug("skip_external", name=item.full_name)
                continue

            category = classify_title(item.title)
            if not is_saveable(category):
                summary.skipped_category += 1
                logger.debug(
                    "skip_category", name=item.full_name, category=category.value
                )
                continue

            candidate = CandidateContact(
                company_id=company_id,
                full_name=item.full_name,
                email=item.email,
                phone=item.phone,
                title=item.title,
                category=category,
                confidence=item.confidence,
                source_document=source_document,
            )
            result = self._dedup.upsert(candidate, filing)
            self._recompute_priority(result.contact)

            if result.merged:
                summary.merged += 1
            else:
                summary.created += 1

        logger.info(
            "ingest_summary",
            company_id=company_id,
            fcc_id=filing.fcc_id,
            created=summary.created,
            merged=summary.merged,
            skipped=summary.skipped_external + summary.skipped_category,
        )
        return summary

    def _recompute_priority(self, contact: object) -> None:
        filing_dates = tuple(
            f.filing_date for f in contact.filings if f.filing_date is not None  # type: ignore[attr-defined]
        )
        contact.priority = compute_priority(  # type: ignore[attr-defined]
            PriorityInput(category=contact.category, filing_dates=filing_dates)  # type: ignore[attr-defined]
        )

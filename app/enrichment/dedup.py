"""Stage 6 — deduplicate people and accumulate their filing references.

Identity rules (in priority order):
  1. same email (case-insensitive), else
  2. same (full_name + company).

When a match is found the existing record is enriched (missing fields are
back-filled, the higher confidence is kept) and the new filing reference is
appended. Otherwise a fresh contact is created.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.db.repositories import ContactRepository
from app.enrichment.classification import classify_title
from app.logging_config import get_logger
from app.models import Contact, Filing
from app.models.enums import ContactCategory

logger = get_logger(__name__)


@dataclass(frozen=True)
class CandidateContact:
    """A person extracted from a document, ready to be merged into the DB."""

    company_id: int
    full_name: str
    email: str | None
    phone: str | None
    title: str | None
    category: ContactCategory
    confidence: int
    source_document: str | None


@dataclass(frozen=True)
class MergeResult:
    """Outcome of :meth:`ContactDeduplicator.upsert`."""

    contact: Contact
    merged: bool


class ContactDeduplicator:
    """Upserts extracted contacts, merging duplicates."""

    def __init__(self, repo: ContactRepository) -> None:
        self._repo = repo

    def _find_existing(self, candidate: CandidateContact) -> Contact | None:
        if candidate.email:
            match = self._repo.find_by_email(candidate.email)
            if match is not None:
                return match
        return self._repo.find_by_name_and_company(
            candidate.full_name, candidate.company_id
        )

    def upsert(self, candidate: CandidateContact, filing: Filing) -> MergeResult:
        """Create or merge ``candidate`` and link it to ``filing``."""
        existing = self._find_existing(candidate)
        if existing is None:
            contact = Contact(
                company_id=candidate.company_id,
                full_name=candidate.full_name,
                email=candidate.email,
                phone=candidate.phone,
                title=candidate.title,
                category=candidate.category,
                confidence=candidate.confidence,
                source_document=candidate.source_document,
            )
            self._link_filing(contact, filing)
            self._repo.add(contact)
            return MergeResult(contact=contact, merged=False)

        self._merge_into(existing, candidate)
        self._link_filing(existing, filing)
        logger.info(
            "duplicate_merged",
            contact_id=existing.id,
            name=existing.full_name,
            email=existing.email,
        )
        return MergeResult(contact=existing, merged=True)

    @staticmethod
    def _merge_into(existing: Contact, candidate: CandidateContact) -> None:
        """Back-fill missing attributes and keep the strongest signal."""
        existing.email = existing.email or candidate.email
        existing.phone = existing.phone or candidate.phone
        if candidate.title and not existing.title:
            existing.title = candidate.title
        # Prefer a more specific (saveable) category over IGNORE.
        if existing.category == ContactCategory.IGNORE and candidate.category != (
            ContactCategory.IGNORE
        ):
            existing.category = candidate.category
        elif existing.title and existing.category == ContactCategory.IGNORE:
            existing.category = classify_title(existing.title)
        existing.confidence = max(existing.confidence, candidate.confidence)

    @staticmethod
    def _link_filing(contact: Contact, filing: Filing) -> None:
        """Append ``filing`` to the contact's filing references if not present."""
        if all(f.id != filing.id for f in contact.filings):
            contact.filings.append(filing)

"""Tests for Stage 6 deduplication."""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.db.repositories import ContactRepository
from app.enrichment.dedup import CandidateContact, ContactDeduplicator
from app.models import Company, Filing
from app.models.enums import ContactCategory


def _candidate(company_id: int, **overrides: object) -> CandidateContact:
    base = dict(
        company_id=company_id,
        full_name="Jane Doe",
        email="jane@u-blox.com",
        phone="+41 44 000",
        title="Certification Manager",
        category=ContactCategory.CERTIFICATION_MANAGER,
        confidence=80,
        source_document="doc1.pdf",
    )
    base.update(overrides)
    return CandidateContact(**base)  # type: ignore[arg-type]


def test_creates_new_contact(session: Session, company: Company, filing: Filing) -> None:
    dedup = ContactDeduplicator(ContactRepository(session))
    result = dedup.upsert(_candidate(company.id), filing)
    assert result.merged is False
    assert result.contact.id is not None
    assert [f.fcc_id for f in result.contact.filings] == [filing.fcc_id]


def test_merges_by_email(session: Session, company: Company, filing: Filing) -> None:
    repo = ContactRepository(session)
    dedup = ContactDeduplicator(repo)
    dedup.upsert(_candidate(company.id, phone=None, confidence=50), filing)

    other = Filing(company_id=company.id, fcc_id="XPYSARA-2", filing_date=date(2024, 1, 1))
    session.add(other)
    session.flush()

    # Same email, higher confidence, new phone, second filing.
    result = dedup.upsert(
        _candidate(company.id, phone="+41 44 999", confidence=95), other
    )
    assert result.merged is True
    assert result.contact.confidence == 95  # keeps the max
    assert result.contact.phone == "+41 44 999"  # back-filled
    assert {f.fcc_id for f in result.contact.filings} == {"XPYNORA-1", "XPYSARA-2"}


def test_merges_by_name_and_company(
    session: Session, company: Company, filing: Filing
) -> None:
    dedup = ContactDeduplicator(ContactRepository(session))
    dedup.upsert(_candidate(company.id, email=None), filing)
    result = dedup.upsert(_candidate(company.id, email=None), filing)
    assert result.merged is True
    # Filing already linked -> not duplicated.
    assert len(result.contact.filings) == 1


def test_different_company_not_merged(session: Session, filing: Filing) -> None:
    c1 = Company(name="Acme")
    c2 = Company(name="Globex")
    session.add_all([c1, c2])
    session.flush()
    dedup = ContactDeduplicator(ContactRepository(session))
    r1 = dedup.upsert(_candidate(c1.id, email=None), filing)
    r2 = dedup.upsert(_candidate(c2.id, email=None), filing)
    assert r2.merged is False
    assert r1.contact.id != r2.contact.id

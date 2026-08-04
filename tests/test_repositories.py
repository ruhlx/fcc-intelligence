"""Tests for the repository layer, including the contact search filters."""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.db.repositories import (
    CompanyRepository,
    ContactRepository,
    DocumentRepository,
    FilingRepository,
)
from app.models import Company, Contact, Filing
from app.models.enums import ContactCategory, DocumentType


def test_company_get_or_create_is_idempotent(session: Session) -> None:
    repo = CompanyRepository(session)
    a = repo.get_or_create("u-blox")
    b = repo.get_or_create("u-blox", country="Switzerland")
    assert a.id == b.id
    assert b.country == "Switzerland"  # back-filled


def test_filing_get_or_create_idempotent(session: Session, company: Company) -> None:
    repo = FilingRepository(session)
    a = repo.get_or_create(company_id=company.id, fcc_id="ABC-1")
    b = repo.get_or_create(company_id=company.id, fcc_id="ABC-1")
    assert a.id == b.id


def test_document_get_or_create_idempotent(session: Session, filing: Filing) -> None:
    repo = DocumentRepository(session)
    a = repo.get_or_create(
        filing_id=filing.id, pdf_url="http://x/a.pdf", doc_type=DocumentType.COVER_LETTER
    )
    b = repo.get_or_create(
        filing_id=filing.id, pdf_url="http://x/a.pdf", doc_type=DocumentType.COVER_LETTER
    )
    assert a.id == b.id
    assert repo.list_for_filing(filing.id) == [a]


def _make_contact(session: Session, company: Company, **kw: object) -> Contact:
    base: dict[str, object] = dict(
        company_id=company.id,
        full_name="Jane Doe",
        email="jane@u-blox.com",
        title="Certification Manager",
        category=ContactCategory.CERTIFICATION_MANAGER,
        confidence=90,
        priority=50,
    )
    base.update(kw)
    c = Contact(**base)  # type: ignore[arg-type]
    session.add(c)
    session.flush()
    return c


def test_contact_search_filters(session: Session, company: Company) -> None:
    _make_contact(session, company)
    other = Company(name="Globex", country="Germany")
    session.add(other)
    session.flush()
    _make_contact(
        session,
        other,
        full_name="Klaus Müller",
        email="klaus@globex.de",
        title="Regulatory Affairs Lead",
        category=ContactCategory.REGULATORY_AFFAIRS,
    )
    repo = ContactRepository(session)

    assert len(repo.search(title="Certification")) == 1
    assert len(repo.search(country="Germany")) == 1
    assert len(repo.search(company="Globex")) == 1
    assert len(repo.search(query="cyber")) == 0
    assert len(repo.search(query="klaus")) == 1
    assert len(repo.search()) == 2


def test_contact_find_by_email_case_insensitive(
    session: Session, company: Company
) -> None:
    _make_contact(session, company)
    repo = ContactRepository(session)
    assert repo.find_by_email("JANE@U-BLOX.COM") is not None


def test_filing_list_ordering(session: Session, company: Company) -> None:
    repo = FilingRepository(session)
    repo.get_or_create(company_id=company.id, fcc_id="OLD", filing_date=date(2020, 1, 1))
    repo.get_or_create(company_id=company.id, fcc_id="NEW", filing_date=date(2025, 1, 1))
    filings = repo.list(company_id=company.id)
    assert filings[0].fcc_id == "NEW"

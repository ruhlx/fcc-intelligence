"""Tests for the ingestion service (Stages 5/6/9 wired together)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.extractor.schemas import ExtractedContact
from app.models import Company, Filing
from app.models.enums import ContactCategory
from app.services.contact_service import ContactIngestionService


def _extracted(**overrides: object) -> ExtractedContact:
    base: dict[str, object] = dict(
        full_name="Jane Doe",
        email="jane@u-blox.com",
        title="Certification Manager",
        is_internal_employee=True,
        confidence=88,
    )
    base.update(overrides)
    return ExtractedContact(**base)  # type: ignore[arg-type]


def test_ingest_saves_saveable_contact(
    session: Session, company: Company, filing: Filing
) -> None:
    svc = ContactIngestionService(session)
    summary = svc.ingest(
        company_id=company.id, filing=filing, extracted=[_extracted()]
    )
    assert summary.created == 1
    assert summary.considered == 1
    saved = svc._repo.find_by_email("jane@u-blox.com")
    assert saved is not None
    assert saved.category == ContactCategory.CERTIFICATION_MANAGER
    # Certification (40) + recent filing (10) = 50.
    assert saved.priority == 50


def test_ingest_skips_external(
    session: Session, company: Company, filing: Filing
) -> None:
    svc = ContactIngestionService(session)
    summary = svc.ingest(
        company_id=company.id,
        filing=filing,
        extracted=[_extracted(is_internal_employee=False)],
    )
    assert summary.skipped_external == 1
    assert summary.created == 0


def test_ingest_stores_non_core_categories_too(
    session: Session, company: Company, filing: Filing
) -> None:
    """Every internal contact is stored, not just the 'core compliance' titles.

    Non-core categories still get their priority (0 base) so they naturally
    sort below Certification/Regulatory/Compliance/Security, but they remain
    in the database and filterable via GET /contacts?category=.
    """
    svc = ContactIngestionService(session)
    summary = svc.ingest(
        company_id=company.id,
        filing=filing,
        extracted=[_extracted(title="Senior RF Engineer")],
    )
    assert summary.created == 1
    saved = svc._repo.find_by_email("jane@u-blox.com")
    assert saved is not None
    assert saved.category == ContactCategory.ENGINEERING


def test_ingest_stores_contact_with_blank_title(
    session: Session, company: Company, filing: Filing
) -> None:
    """A name/email with no usable title still gets stored (category IGNORE)."""
    svc = ContactIngestionService(session)
    summary = svc.ingest(
        company_id=company.id, filing=filing, extracted=[_extracted(title=None)]
    )
    assert summary.created == 1
    saved = svc._repo.find_by_email("jane@u-blox.com")
    assert saved is not None
    assert saved.category == ContactCategory.IGNORE


def test_ingest_merges_duplicate(
    session: Session, company: Company, filing: Filing
) -> None:
    svc = ContactIngestionService(session)
    svc.ingest(company_id=company.id, filing=filing, extracted=[_extracted()])
    summary = svc.ingest(
        company_id=company.id, filing=filing, extracted=[_extracted(confidence=99)]
    )
    assert summary.merged == 1
    assert svc._repo.find_by_email("jane@u-blox.com").confidence == 99

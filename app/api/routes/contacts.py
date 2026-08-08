"""Contact endpoints (Stage 7)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.db.repositories import ContactRepository
from app.models.enums import ContactCategory
from app.services.schemas import ContactOut

router = APIRouter(tags=["contacts"])


@router.get("/contacts", response_model=list[ContactOut])
def list_contacts(
    title: str | None = Query(default=None, description="Substring match on job title."),
    country: str | None = Query(default=None),
    company: str | None = Query(default=None, description="Substring match on company."),
    category: ContactCategory | None = Query(
        default=None, description="Exact classified category, e.g. CERTIFICATION_MANAGER."
    ),
    session: Session = Depends(db_session),
) -> list[ContactOut]:
    """List contacts with optional title / country / company / category filters.

    All contacts (every classified category) are stored, so ``category`` is how
    you narrow to just the compliance-relevant ones when you want to.

    Examples: ``/contacts?title=Certification``, ``/contacts?country=Germany``,
    ``/contacts?company=u-blox``, ``/contacts?category=CERTIFICATION_MANAGER``.
    """
    contacts = ContactRepository(session).search(
        title=title, country=country, company=company, category=category
    )
    return [ContactOut.from_contact(c) for c in contacts]

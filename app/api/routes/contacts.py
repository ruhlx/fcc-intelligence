"""Contact endpoints (Stage 7)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.db.repositories import ContactRepository
from app.services.schemas import ContactOut

router = APIRouter(tags=["contacts"])


@router.get("/contacts", response_model=list[ContactOut])
def list_contacts(
    title: str | None = Query(default=None, description="Substring match on job title."),
    country: str | None = Query(default=None),
    company: str | None = Query(default=None, description="Substring match on company."),
    session: Session = Depends(db_session),
) -> list[ContactOut]:
    """List contacts with optional title / country / company filters.

    Examples: ``/contacts?title=Certification``, ``/contacts?country=Germany``,
    ``/contacts?company=u-blox``.
    """
    contacts = ContactRepository(session).search(
        title=title, country=country, company=company
    )
    return [ContactOut.from_contact(c) for c in contacts]

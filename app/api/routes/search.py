"""Free-text search and CSV export endpoints (Stages 7 & 8)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.db.repositories import ContactRepository
from app.services.export_service import ExportService
from app.services.schemas import ContactOut

router = APIRouter(tags=["search"])


@router.get("/search", response_model=list[ContactOut])
def search_contacts(
    q: str = Query(..., min_length=1, description="Free-text query, e.g. 'cyber'."),
    session: Session = Depends(db_session),
) -> list[ContactOut]:
    """Free-text search across contact name, title and email."""
    contacts = ContactRepository(session).search(query=q)
    return [ContactOut.from_contact(c) for c in contacts]


@router.get("/export/contacts.csv", response_class=PlainTextResponse)
def export_contacts_csv(session: Session = Depends(db_session)) -> PlainTextResponse:
    """Download the contacts database as CSV (Stage 8)."""
    csv_text = ExportService(session).to_csv_string()
    return PlainTextResponse(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=contacts.csv"},
    )

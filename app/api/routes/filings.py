"""Filing endpoints (Stage 7)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.db.repositories import FilingRepository
from app.services.schemas import FilingOut

router = APIRouter(tags=["filings"])


@router.get("/filings", response_model=list[FilingOut])
def list_filings(
    company_id: int | None = Query(default=None),
    session: Session = Depends(db_session),
) -> list[FilingOut]:
    """List filings, optionally scoped to a company."""
    filings = FilingRepository(session).list(company_id=company_id)
    return [FilingOut.model_validate(f) for f in filings]

"""Company endpoints (Stage 7)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.db.repositories import CompanyRepository
from app.services.schemas import CompanyOut

router = APIRouter(tags=["companies"])


@router.get("/companies", response_model=list[CompanyOut])
def list_companies(
    country: str | None = Query(default=None),
    session: Session = Depends(db_session),
) -> list[CompanyOut]:
    """List all companies, optionally filtered by country."""
    companies = CompanyRepository(session).list(country=country)
    return [CompanyOut.model_validate(c) for c in companies]


@router.get("/company/{company_id}", response_model=CompanyOut)
def get_company(
    company_id: int, session: Session = Depends(db_session)
) -> CompanyOut:
    """Return a single company by id."""
    company = CompanyRepository(session).get(company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    return CompanyOut.model_validate(company)

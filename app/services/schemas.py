"""Pydantic response models for the REST API (Stage 7)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict


class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    country: str | None = None
    website: str | None = None


class FilingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fcc_id: str
    product_name: str | None = None
    filing_date: date | None = None
    filing_url: str | None = None
    company_id: int


class ContactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str | None = None
    phone: str | None = None
    title: str | None = None
    category: str
    confidence: int
    priority: int
    company: CompanyOut
    fcc_ids: list[str] = []

    @classmethod
    def from_contact(cls, contact: object) -> ContactOut:
        """Build from a :class:`~app.models.Contact` including its FCC IDs."""
        fcc_ids = [f.fcc_id for f in getattr(contact, "filings", [])]
        base = cls.model_validate(contact)
        return base.model_copy(update={"fcc_ids": fcc_ids})

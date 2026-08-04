"""Company repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company


class CompanyRepository:
    """Persistence operations for :class:`Company`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, company_id: int) -> Company | None:
        """Return a company by primary key, or ``None``."""
        return self._session.get(Company, company_id)

    def get_by_name(self, name: str) -> Company | None:
        """Return a company by exact (case-sensitive) name."""
        stmt = select(Company).where(Company.name == name)
        return self._session.scalar(stmt)

    def get_or_create(
        self, name: str, *, country: str | None = None, website: str | None = None
    ) -> Company:
        """Return the existing company with ``name`` or create a new one."""
        company = self.get_by_name(name)
        if company is not None:
            # Backfill any newly-discovered attributes.
            if country and not company.country:
                company.country = country
            if website and not company.website:
                company.website = website
            return company
        company = Company(name=name, country=country, website=website)
        self._session.add(company)
        self._session.flush()
        return company

    def list(self, *, country: str | None = None) -> list[Company]:
        """List companies, optionally filtered by country."""
        stmt = select(Company).order_by(Company.name)
        if country:
            stmt = stmt.where(Company.country == country)
        return list(self._session.scalars(stmt))

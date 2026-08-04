"""Filing repository."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Filing


class FilingRepository:
    """Persistence operations for :class:`Filing`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_fcc_id(self, fcc_id: str) -> Filing | None:
        """Return a filing by its unique FCC ID."""
        stmt = select(Filing).where(Filing.fcc_id == fcc_id)
        return self._session.scalar(stmt)

    def get_or_create(
        self,
        *,
        company_id: int,
        fcc_id: str,
        product_name: str | None = None,
        filing_date: date | None = None,
        filing_url: str | None = None,
    ) -> Filing:
        """Idempotently create a filing keyed on ``fcc_id``."""
        filing = self.get_by_fcc_id(fcc_id)
        if filing is not None:
            return filing
        filing = Filing(
            company_id=company_id,
            fcc_id=fcc_id,
            product_name=product_name,
            filing_date=filing_date,
            filing_url=filing_url,
        )
        self._session.add(filing)
        self._session.flush()
        return filing

    def list(self, *, company_id: int | None = None) -> list[Filing]:
        """List filings, optionally scoped to a company."""
        stmt = select(Filing).order_by(Filing.filing_date.desc().nullslast())
        if company_id is not None:
            stmt = stmt.where(Filing.company_id == company_id)
        return list(self._session.scalars(stmt))

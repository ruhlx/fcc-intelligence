"""Contact repository — includes the deduplication lookups used in Stage 6."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models import Company, Contact
from app.models.enums import ContactCategory


class ContactRepository:
    """Persistence and query operations for :class:`Contact`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_email(self, email: str) -> Contact | None:
        """Return a contact matching ``email`` (case-insensitive)."""
        stmt = select(Contact).where(func.lower(Contact.email) == email.lower())
        return self._session.scalar(stmt)

    def find_by_name_and_company(self, full_name: str, company_id: int) -> Contact | None:
        """Return a contact matching (name, company), case-insensitive on name."""
        stmt = select(Contact).where(
            func.lower(Contact.full_name) == full_name.lower(),
            Contact.company_id == company_id,
        )
        return self._session.scalar(stmt)

    def add(self, contact: Contact) -> Contact:
        """Add a new contact and flush to assign its primary key."""
        self._session.add(contact)
        self._session.flush()
        return contact

    def get(self, contact_id: int) -> Contact | None:
        """Return a contact by primary key."""
        return self._session.get(Contact, contact_id)

    def search(
        self,
        *,
        title: str | None = None,
        country: str | None = None,
        company: str | None = None,
        category: ContactCategory | None = None,
        query: str | None = None,
    ) -> list[Contact]:
        """Flexible search backing the REST filters (Stages 7).

        All filters are combined with AND. ``query`` performs a free-text
        ``ILIKE`` over name, title and email.
        """
        stmt = (
            select(Contact)
            .join(Company, Contact.company_id == Company.id)
            .options(joinedload(Contact.company), joinedload(Contact.filings))
            .order_by(Contact.priority.desc(), Contact.full_name)
        )
        if title:
            stmt = stmt.where(Contact.title.ilike(f"%{title}%"))
        if country:
            stmt = stmt.where(Company.country == country)
        if company:
            stmt = stmt.where(Company.name.ilike(f"%{company}%"))
        if category is not None:
            stmt = stmt.where(Contact.category == category)
        if query:
            like = f"%{query}%"
            stmt = stmt.where(
                or_(
                    Contact.full_name.ilike(like),
                    Contact.title.ilike(like),
                    Contact.email.ilike(like),
                )
            )
        return list(self._session.scalars(stmt).unique())

    def all_saveable(self) -> list[Contact]:
        """Return every persisted (already-filtered) contact for CSV export."""
        stmt = (
            select(Contact)
            .options(joinedload(Contact.company), joinedload(Contact.filings))
            .order_by(Contact.priority.desc())
        )
        return list(self._session.scalars(stmt).unique())

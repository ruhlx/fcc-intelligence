"""Filing ORM model plus the contact<->filing association table."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Column, Date, ForeignKey, String, Table, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.contact import Contact
    from app.models.document import Document


# Stage 6: many-to-many linking deduplicated contacts to the filings they appear in.
contact_filings = Table(
    "contact_filings",
    Base.metadata,
    Column("contact_id", ForeignKey("contacts.id", ondelete="CASCADE"), primary_key=True),
    Column("filing_id", ForeignKey("filings.id", ondelete="CASCADE"), primary_key=True),
)


class Filing(Base, TimestampMixin):
    """A single FCC Equipment Authorization filing, keyed by FCC ID."""

    __tablename__ = "filings"
    __table_args__ = (UniqueConstraint("fcc_id", name="uq_filings_fcc_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    fcc_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    product_name: Mapped[str | None] = mapped_column(String(512))
    filing_date: Mapped[date | None] = mapped_column(Date, index=True)
    filing_url: Mapped[str | None] = mapped_column(String(1024))

    company: Mapped[Company] = relationship(back_populates="filings")
    documents: Mapped[list[Document]] = relationship(
        back_populates="filing", cascade="all, delete-orphan"
    )
    contacts: Mapped[list[Contact]] = relationship(
        secondary=contact_filings, back_populates="filings"
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Filing id={self.id} fcc_id={self.fcc_id!r}>"

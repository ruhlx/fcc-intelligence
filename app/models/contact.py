"""Contact ORM model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import ContactCategory

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.filing import Filing


class Contact(Base, TimestampMixin):
    """A deduplicated person responsible for product compliance/certification."""

    __tablename__ = "contacts"
    __table_args__ = (
        # Stage 6: identity is email, or (name + company) when email is absent.
        UniqueConstraint("company_id", "full_name", name="uq_contacts_company_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    full_name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(320), index=True)
    phone: Mapped[str | None] = mapped_column(String(64))
    title: Mapped[str | None] = mapped_column(String(256))
    category: Mapped[ContactCategory] = mapped_column(
        SAEnum(ContactCategory, name="contact_category"),
        default=ContactCategory.IGNORE,
        index=True,
    )
    confidence: Mapped[int] = mapped_column(Integer, default=0)
    priority: Mapped[int] = mapped_column(Integer, default=0, index=True)
    source_document: Mapped[str | None] = mapped_column(String(1024))

    company: Mapped[Company] = relationship(back_populates="contacts")
    filings: Mapped[list[Filing]] = relationship(
        secondary="contact_filings", back_populates="contacts"
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Contact id={self.id} name={self.full_name!r} cat={self.category.value}>"

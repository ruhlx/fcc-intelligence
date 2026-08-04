"""Company ORM model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.contact import Contact
    from app.models.filing import Filing


class Company(Base, TimestampMixin):
    """A manufacturer / applicant that holds FCC equipment authorizations."""

    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False, unique=True, index=True)
    country: Mapped[str | None] = mapped_column(String(128), index=True)
    website: Mapped[str | None] = mapped_column(String(512))

    filings: Mapped[list[Filing]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    contacts: Mapped[list[Contact]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Company id={self.id} name={self.name!r}>"

"""Document ORM model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import DocumentType

if TYPE_CHECKING:
    from app.models.filing import Filing


class Document(Base, TimestampMixin):
    """A PDF exhibit belonging to a filing, plus its extracted text."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    filing_id: Mapped[int] = mapped_column(
        ForeignKey("filings.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[DocumentType] = mapped_column(
        SAEnum(DocumentType, name="document_type"), default=DocumentType.OTHER
    )
    pdf_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    local_path: Mapped[str | None] = mapped_column(String(1024))
    parsed_text: Mapped[str | None] = mapped_column(Text)

    filing: Mapped[Filing] = relationship(back_populates="documents")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Document id={self.id} type={self.type.value}>"

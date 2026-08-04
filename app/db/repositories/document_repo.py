"""Document repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Document
from app.models.enums import DocumentType


class DocumentRepository:
    """Persistence operations for :class:`Document`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_url(self, filing_id: int, pdf_url: str) -> Document | None:
        """Return a document for ``filing_id`` with the given URL, if present."""
        stmt = select(Document).where(
            Document.filing_id == filing_id, Document.pdf_url == pdf_url
        )
        return self._session.scalar(stmt)

    def get_or_create(
        self, *, filing_id: int, pdf_url: str, doc_type: DocumentType
    ) -> Document:
        """Idempotently create a document keyed on (filing, url)."""
        document = self.get_by_url(filing_id, pdf_url)
        if document is not None:
            return document
        document = Document(filing_id=filing_id, pdf_url=pdf_url, type=doc_type)
        self._session.add(document)
        self._session.flush()
        return document

    def list_for_filing(self, filing_id: int) -> list[Document]:
        """Return all documents attached to a filing."""
        stmt = select(Document).where(Document.filing_id == filing_id)
        return list(self._session.scalars(stmt))

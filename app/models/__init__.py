"""ORM models package.

Importing this package registers every model on :data:`Base.metadata`, which is
required for Alembic autogeneration and for ``Base.metadata.create_all``.
"""

from app.models.base import Base
from app.models.company import Company
from app.models.contact import Contact
from app.models.document import Document
from app.models.enums import ContactCategory, DocumentType
from app.models.filing import Filing, contact_filings

__all__ = [
    "Base",
    "Company",
    "Contact",
    "ContactCategory",
    "Document",
    "DocumentType",
    "Filing",
    "contact_filings",
]

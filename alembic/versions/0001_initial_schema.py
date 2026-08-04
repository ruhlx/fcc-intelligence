"""Initial schema: companies, filings, documents, contacts, contact_filings.

Revision ID: 0001
Revises:
Create Date: 2026-08-04
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONTACT_CATEGORY = sa.Enum(
    "CERTIFICATION_MANAGER",
    "PRODUCT_COMPLIANCE",
    "REGULATORY_AFFAIRS",
    "PRODUCT_SECURITY",
    "QUALITY",
    "ENGINEERING",
    "EXECUTIVE",
    "IGNORE",
    name="contact_category",
)

DOCUMENT_TYPE = sa.Enum(
    "AUTHORIZATION_LETTER",
    "COVER_LETTER",
    "CONFIDENTIALITY_REQUEST",
    "DECLARATION",
    "ATTESTATION",
    "CE_DOC",
    "TUV_CERTIFICATE",
    "UL_CERTIFICATE",
    "SGS_CERTIFICATE",
    "INTERTEK_CERTIFICATE",
    "EUROFINS_CERTIFICATE",
    "DEKRA_CERTIFICATE",
    "OTHER",
    name="document_type",
)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("country", sa.String(128)),
        sa.Column("website", sa.String(512)),
        *_timestamps(),
        sa.UniqueConstraint("name", name="uq_companies_name"),
    )
    op.create_index("ix_companies_name", "companies", ["name"])
    op.create_index("ix_companies_country", "companies", ["country"])

    op.create_table(
        "filings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fcc_id", sa.String(64), nullable=False),
        sa.Column("product_name", sa.String(512)),
        sa.Column("filing_date", sa.Date()),
        sa.Column("filing_url", sa.String(1024)),
        *_timestamps(),
        sa.UniqueConstraint("fcc_id", name="uq_filings_fcc_id"),
    )
    op.create_index("ix_filings_company_id", "filings", ["company_id"])
    op.create_index("ix_filings_fcc_id", "filings", ["fcc_id"])
    op.create_index("ix_filings_filing_date", "filings", ["filing_date"])

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("filing_id", sa.Integer(),
                  sa.ForeignKey("filings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", DOCUMENT_TYPE, nullable=False, server_default="OTHER"),
        sa.Column("pdf_url", sa.String(1024), nullable=False),
        sa.Column("local_path", sa.String(1024)),
        sa.Column("parsed_text", sa.Text()),
        *_timestamps(),
    )
    op.create_index("ix_documents_filing_id", "documents", ["filing_id"])

    op.create_table(
        "contacts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("full_name", sa.String(256), nullable=False),
        sa.Column("email", sa.String(320)),
        sa.Column("phone", sa.String(64)),
        sa.Column("title", sa.String(256)),
        sa.Column("category", CONTACT_CATEGORY, nullable=False, server_default="IGNORE"),
        sa.Column("confidence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_document", sa.String(1024)),
        *_timestamps(),
        sa.UniqueConstraint("company_id", "full_name", name="uq_contacts_company_name"),
    )
    op.create_index("ix_contacts_company_id", "contacts", ["company_id"])
    op.create_index("ix_contacts_full_name", "contacts", ["full_name"])
    op.create_index("ix_contacts_email", "contacts", ["email"])
    op.create_index("ix_contacts_category", "contacts", ["category"])
    op.create_index("ix_contacts_priority", "contacts", ["priority"])

    op.create_table(
        "contact_filings",
        sa.Column("contact_id", sa.Integer(),
                  sa.ForeignKey("contacts.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("filing_id", sa.Integer(),
                  sa.ForeignKey("filings.id", ondelete="CASCADE"), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("contact_filings")
    op.drop_table("contacts")
    op.drop_table("documents")
    op.drop_table("filings")
    op.drop_table("companies")
    DOCUMENT_TYPE.drop(op.get_bind(), checkfirst=True)
    CONTACT_CATEGORY.drop(op.get_bind(), checkfirst=True)

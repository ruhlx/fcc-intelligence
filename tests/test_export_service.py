"""Tests for Stage 8 CSV export."""

from __future__ import annotations

import csv
import io

from sqlalchemy.orm import Session

from app.extractor.schemas import ExtractedContact
from app.models import Company, Filing
from app.services.contact_service import ContactIngestionService
from app.services.export_service import CSV_COLUMNS, ExportService


def test_csv_header_and_row(
    session: Session, company: Company, filing: Filing
) -> None:
    ContactIngestionService(session).ingest(
        company_id=company.id,
        filing=filing,
        extracted=[
            ExtractedContact(
                full_name="Jane Doe",
                email="jane@u-blox.com",
                phone="+41 44 000",
                title="Certification Manager",
                confidence=88,
            )
        ],
    )
    csv_text = ExportService(session).to_csv_string()
    reader = csv.DictReader(io.StringIO(csv_text))
    assert reader.fieldnames == CSV_COLUMNS
    rows = list(reader)
    assert len(rows) == 1
    row = rows[0]
    assert row["Company"] == "u-blox"
    assert row["Country"] == "Switzerland"
    assert row["Name"] == "Jane Doe"
    assert row["Email"] == "jane@u-blox.com"
    assert row["Website"] == "https://u-blox.com"
    assert row["FCC IDs"] == "XPYNORA-1"
    assert row["Number of filings"] == "1"
    assert row["Priority"] == "50"


def test_write_csv_to_file(session: Session, tmp_path) -> None:
    out = tmp_path / "contacts.csv"
    path = ExportService(session).write_csv(out)
    assert path.exists()
    assert path.read_text().startswith("Company,Country,Name")

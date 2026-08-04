"""Stage 8 — CSV export of the contact database."""

from __future__ import annotations

import csv
import io
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.repositories import ContactRepository
from app.logging_config import get_logger
from app.models import Contact

logger = get_logger(__name__)

CSV_COLUMNS = [
    "Company",
    "Country",
    "Name",
    "Title",
    "Email",
    "Phone",
    "Website",
    "FCC IDs",
    "Number of filings",
    "Priority",
]


def _contact_row(contact: Contact) -> dict[str, str]:
    fcc_ids = sorted({f.fcc_id for f in contact.filings})
    return {
        "Company": contact.company.name if contact.company else "",
        "Country": contact.company.country or "" if contact.company else "",
        "Name": contact.full_name,
        "Title": contact.title or "",
        "Email": contact.email or "",
        "Phone": contact.phone or "",
        "Website": contact.company.website or "" if contact.company else "",
        "FCC IDs": "; ".join(fcc_ids),
        "Number of filings": str(len(fcc_ids)),
        "Priority": str(contact.priority),
    }


class ExportService:
    """Renders the contacts table to CSV."""

    def __init__(self, session: Session) -> None:
        self._repo = ContactRepository(session)

    def to_csv_string(self) -> str:
        """Return the full contacts export as a CSV string."""
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        count = 0
        for contact in self._repo.all_saveable():
            writer.writerow(_contact_row(contact))
            count += 1
        logger.info("csv_export", rows=count)
        return buffer.getvalue()

    def write_csv(self, path: Path) -> Path:
        """Write ``contacts.csv`` to ``path`` and return the path."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_csv_string(), encoding="utf-8")
        return path

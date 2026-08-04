"""Pure HTML-parsing helpers for the FCC EAS pages.

These functions take raw HTML and return typed rows. They contain **no** I/O so
they can be unit-tested against saved HTML fixtures.

The FCC Equipment Authorization System (EAS) is an unofficial, HTML-only
interface; selectors are intentionally lenient and defensive.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from app.models.enums import DocumentType

_FCC_ID_RE = re.compile(r"\b([A-Z0-9\-]{3,7})[-\s]?([A-Z0-9\-]{1,16})\b")
_DATE_FORMATS = ("%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y")


@dataclass(frozen=True)
class ApplicationRow:
    """One row of an EAS Generic Search result."""

    fcc_id: str
    application_id: str | None
    grantee_name: str | None
    product_name: str | None
    filing_date: date | None
    detail_url: str | None


@dataclass(frozen=True)
class ExhibitRow:
    """One exhibit (attachment) belonging to an application."""

    description: str
    doc_type: DocumentType
    pdf_url: str


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    value = value.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _cell_text(cell: Tag | None) -> str | None:
    if cell is None:
        return None
    text = cell.get_text(" ", strip=True)
    return text or None


def classify_document(description: str) -> DocumentType:
    """Map an exhibit description string to a :class:`DocumentType`."""
    text = (description or "").lower()
    table: tuple[tuple[DocumentType, tuple[str, ...]], ...] = (
        (DocumentType.AUTHORIZATION_LETTER, ("authorization letter", "auth letter", "poa",
                                             "letter of authorization", "agent auth")),
        (DocumentType.COVER_LETTER, ("cover letter",)),
        (DocumentType.CONFIDENTIALITY_REQUEST, ("confidential", "confidentiality")),
        (DocumentType.DECLARATION, ("declaration", "doc")),
        (DocumentType.ATTESTATION, ("attestation", "attest")),
    )
    for doc_type, keywords in table:
        if any(kw in text for kw in keywords):
            return doc_type
    return DocumentType.OTHER


def parse_search_results(html: str, *, base_url: str) -> list[ApplicationRow]:
    """Parse an EAS ``GenericSearchResult.cfm`` page into application rows."""
    soup = BeautifulSoup(html, "html.parser")
    rows: list[ApplicationRow] = []
    seen: set[str] = set()

    for tr in soup.find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) < 2:
            continue
        link = tr.find("a", href=True)
        detail_url = urljoin(base_url, str(link["href"])) if link else None

        # The detail link carries the authoritative fcc_id; fall back to
        # reconstructing it from the first two (grantee + product) columns.
        fcc_id = _extract_query_param(detail_url, "fcc_id")
        if not fcc_id:
            combined = "".join((_cell_text(c) or "") for c in cells[:2]).replace(" ", "")
            match = _FCC_ID_RE.search(combined)
            if not match:
                continue
            fcc_id = f"{match.group(1)}{match.group(2)}"
        if fcc_id in seen:
            continue
        seen.add(fcc_id)

        rows.append(
            ApplicationRow(
                fcc_id=fcc_id,
                application_id=_extract_query_param(detail_url, "application_id"),
                grantee_name=_cell_text(cells[2]) if len(cells) > 2 else None,
                product_name=_cell_text(cells[3]) if len(cells) > 3 else None,
                filing_date=_first_date(cells),
                detail_url=detail_url,
            )
        )
    return rows


def _first_date(cells: list[Tag]) -> date | None:
    """Return the first cell whose text parses as a date."""
    for cell in cells:
        parsed = _parse_date(_cell_text(cell))
        if parsed is not None:
            return parsed
    return None


def parse_exhibit_list(html: str, *, base_url: str) -> list[ExhibitRow]:
    """Parse an EAS exhibit report into a list of downloadable attachments."""
    soup = BeautifulSoup(html, "html.parser")
    exhibits: list[ExhibitRow] = []
    seen: set[str] = set()

    for link in soup.find_all("a", href=True):
        href = str(link["href"])
        if "GetApplicationAttachment" not in href and not href.lower().endswith(".pdf"):
            continue
        pdf_url = urljoin(base_url, href)
        if pdf_url in seen:
            continue
        seen.add(pdf_url)

        # Prefer the surrounding row's description cell over the link text.
        description = _row_description(link) or link.get_text(" ", strip=True)
        exhibits.append(
            ExhibitRow(
                description=description,
                doc_type=classify_document(description),
                pdf_url=pdf_url,
            )
        )
    return exhibits


def _row_description(link: Tag) -> str | None:
    row = link.find_parent("tr")
    if row is None:
        return None
    cells = [c.get_text(" ", strip=True) for c in row.find_all("td")]
    text = " ".join(c for c in cells if c)
    return text or None


def _extract_query_param(url: str | None, key: str) -> str | None:
    if not url:
        return None
    match = re.search(rf"{re.escape(key)}=([^&]+)", url)
    return match.group(1) if match else None

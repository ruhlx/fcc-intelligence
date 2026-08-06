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
    country: str | None = None
    city: str | None = None
    # The "View Form" (731) page carries the structured Responsible Party
    # contact (name, title, email, phone) — often the best lead per filing.
    form_url: str | None = None


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
    """Parse an EAS ``GenericSearchResult.cfm`` page into application rows.

    Each filing is anchored on its "Display Exhibits" link
    (``ViewExhibitReport.cfm?mode=Exhibits&application_id=…&fcc_id=…``), which
    carries the authoritative FCC ID and application id. Applicant / country /
    date are read from the surrounding row relative to the FCC-ID cell, so the
    parser is robust to the page's many spacer columns.
    """
    soup = BeautifulSoup(html, "html.parser")
    rows: list[ApplicationRow] = []
    seen: set[str] = set()

    for link in soup.find_all("a", href=True):
        href = str(link["href"])
        if "ViewExhibitReport.cfm" not in href or "mode=Exhibits" not in href:
            continue
        fcc_id = _extract_query_param(href, "fcc_id")
        if not fcc_id or fcc_id in seen:
            continue
        seen.add(fcc_id)

        row = link.find_parent("tr")
        values = (
            [txt for c in row.find_all("td") if (txt := c.get_text(" ", strip=True))]
            if row is not None
            else []
        )
        applicant, city, country, filing_date = _row_fields(values, fcc_id)

        form_link = row.find("a", href=lambda h: h and "GetTcb731Report.do" in h) if row else None
        form_url = urljoin(base_url, str(form_link["href"])) if form_link else None

        rows.append(
            ApplicationRow(
                fcc_id=fcc_id,
                application_id=_extract_query_param(href, "application_id"),
                grantee_name=applicant,
                product_name=None,
                filing_date=filing_date,
                detail_url=urljoin(base_url, href),
                country=country,
                city=city,
                form_url=form_url,
            )
        )
    return rows


def _row_fields(
    values: list[str], fcc_id: str
) -> tuple[str | None, str | None, str | None, date | None]:
    """Extract (applicant, city, country, date) from a row's non-empty cells.

    Columns run: … Applicant, Address, City, State, Country, Zip, FCC ID,
    Purpose, Final Action Date, … so we locate the FCC-ID cell and read the
    others at fixed offsets from it.
    """
    try:
        i = values.index(fcc_id)
    except ValueError:
        return None, None, None, None
    applicant = values[i - 5] if i - 5 >= 0 else None
    city = values[i - 4] if i - 4 >= 0 else None
    country = values[i - 2] if i - 2 >= 0 else None
    filing_date = _parse_date(values[i + 2]) if i + 2 < len(values) else None
    return applicant, city, country, filing_date


@dataclass(frozen=True)
class FormContact:
    """A contact parsed structurally from a 731 application form."""

    full_name: str
    title: str | None
    email: str | None
    phone: str | None


def parse_application_form(html: str) -> list[FormContact]:
    """Extract the Responsible Party contact(s) from a 731 "View Form" page.

    The form is a label/value table. Empty ``Contact`` sections have blank
    values, so each block with a non-empty ``Last Name`` is a real person; we
    read the adjacent First Name / Title / Email / Telephone fields (skipping
    blanks) around that anchor.
    """
    soup = BeautifulSoup(html, "html.parser")
    pairs: list[tuple[str, str]] = []
    for tr in soup.find_all("tr"):
        cells = tr.find_all(["td", "th"])
        if len(cells) < 2:
            continue
        label = cells[0].get_text(" ", strip=True)
        if label.endswith(":"):
            pairs.append((label.rstrip(":").strip().lower(), cells[1].get_text(" ", strip=True)))

    contacts: list[FormContact] = []
    seen: set[str] = set()
    for i, (label, value) in enumerate(pairs):
        if label != "last name" or not value:
            continue
        window = pairs[max(0, i - 4) : i + 8]

        def _find(names: set[str], win: list[tuple[str, str]] = window) -> str | None:
            return next((v for k, v in win if k in names and v), None)

        first = _find({"first name"})
        # Some forms put the whole name in "First Name"; avoid "Jake Bascon Bascon".
        if first and value.lower() in first.lower():
            full_name = first
        elif first:
            full_name = f"{first} {value}".strip()
        else:
            full_name = value
        key = full_name.lower()
        if key in seen:
            continue
        seen.add(key)
        contacts.append(
            FormContact(
                full_name=full_name,
                title=_find({"title"}),
                email=_find({"email", "e-mail"}),
                phone=_find({"telephone number", "telephone"}),
            )
        )
    return contacts


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

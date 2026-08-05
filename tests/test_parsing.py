"""Tests for the FCC HTML parsers, against real captured EAS pages."""

from __future__ import annotations

from pathlib import Path

from app.crawler.parsing import (
    classify_document,
    parse_exhibit_list,
    parse_search_results,
)
from app.models.enums import DocumentType

FIXTURES = Path(__file__).parent / "fixtures"
SEARCH_HTML = (FIXTURES / "fcc_search_result.html").read_text()
EXHIBIT_HTML = (FIXTURES / "fcc_exhibit_report.html").read_text()

SEARCH_BASE = "https://apps.fcc.gov/oetcf/eas/reports/GenericSearchResult.cfm"
EXHIBIT_BASE = "https://apps.fcc.gov/oetcf/eas/reports/ViewExhibitReport.cfm"


def test_parse_search_results_extracts_filings() -> None:
    rows = parse_search_results(SEARCH_HTML, base_url=SEARCH_BASE)
    assert len(rows) >= 5
    by_id = {r.fcc_id: r for r in rows}
    assert "XPYEMMYW163" in by_id
    row = by_id["XPYEMMYW163"]
    assert row.grantee_name == "u-blox AG"
    assert row.country == "Switzerland"
    assert row.city == "Thalwil"
    assert row.filing_date is not None and row.filing_date.year == 2017
    # detail_url is the Display-Exhibits page and carries the application id.
    assert row.detail_url is not None and "ViewExhibitReport" in row.detail_url
    assert row.application_id


def test_parse_search_results_dedupes_by_fcc_id() -> None:
    rows = parse_search_results(SEARCH_HTML, base_url=SEARCH_BASE)
    ids = [r.fcc_id for r in rows]
    assert len(ids) == len(set(ids))


def test_parse_search_results_empty() -> None:
    assert parse_search_results("<html><body>no results</body></html>", base_url=SEARCH_BASE) == []


def test_parse_exhibit_list_finds_attachments() -> None:
    exhibits = parse_exhibit_list(EXHIBIT_HTML, base_url=EXHIBIT_BASE)
    assert len(exhibits) >= 3
    assert all("GetApplicationAttachment" in e.pdf_url for e in exhibits)
    # At least one recognisable regulatory doc type was classified.
    assert any(e.doc_type != DocumentType.OTHER for e in exhibits)


def test_classify_document() -> None:
    assert classify_document("Cover Letter") == DocumentType.COVER_LETTER
    assert classify_document("Letter of Authorization") == DocumentType.AUTHORIZATION_LETTER
    assert classify_document("Confidentiality Request") == DocumentType.CONFIDENTIALITY_REQUEST
    assert classify_document("SAR Attestation Statement") == DocumentType.ATTESTATION
    assert classify_document("Internal Photos") == DocumentType.OTHER

"""Tests for the pure FCC HTML parsers."""

from __future__ import annotations

from app.crawler.parsing import (
    classify_document,
    parse_exhibit_list,
    parse_search_results,
)
from app.models.enums import DocumentType

SEARCH_HTML = """
<html><body>
<table>
  <tr><th>Grantee</th><th>Product</th><th>Applicant</th><th>Product</th><th>Date</th></tr>
  <tr>
    <td>XPY</td><td>NORA-1</td>
    <td>u-blox AG</td><td>GNSS Module</td><td>01/15/2025</td>
    <td><a href="GenericSearchResult.cfm?application_id=1234&fcc_id=XPYNORA-1">detail</a></td>
  </tr>
  <tr>
    <td>XPY</td><td>SARA-2</td>
    <td>u-blox AG</td><td>Cellular Module</td><td>03/02/2024</td>
    <td><a href="GenericSearchResult.cfm?application_id=5678&fcc_id=XPYSARA-2">detail</a></td>
  </tr>
</table>
</body></html>
"""

EXHIBIT_HTML = """
<html><body>
<table>
  <tr><td>Cover Letter</td>
      <td><a href="GetApplicationAttachment.html?id=111">Download</a></td></tr>
  <tr><td>Authorization Letter (POA)</td>
      <td><a href="GetApplicationAttachment.html?id=222">Download</a></td></tr>
  <tr><td>Confidentiality Request Long Term</td>
      <td><a href="GetApplicationAttachment.html?id=333">Download</a></td></tr>
  <tr><td>Internal Photos</td>
      <td><a href="https://example.com/notapdf.jpg">image</a></td></tr>
</table>
</body></html>
"""


def test_parse_search_results() -> None:
    rows = parse_search_results(SEARCH_HTML, base_url="https://apps.fcc.gov/x/Search.cfm")
    assert len(rows) == 2
    first = rows[0]
    assert first.fcc_id == "XPYNORA-1"
    assert first.application_id == "1234"
    assert first.grantee_name == "u-blox AG"
    assert first.filing_date is not None
    assert first.filing_date.year == 2025
    assert first.detail_url is not None and "application_id=1234" in first.detail_url


def test_parse_search_results_dedupes() -> None:
    doubled = SEARCH_HTML + SEARCH_HTML
    rows = parse_search_results(doubled, base_url="https://apps.fcc.gov/x/Search.cfm")
    assert len(rows) == 2


def test_parse_exhibit_list_filters_non_pdf() -> None:
    exhibits = parse_exhibit_list(EXHIBIT_HTML, base_url="https://apps.fcc.gov/x/View.cfm")
    urls = [e.pdf_url for e in exhibits]
    assert len(exhibits) == 3  # the .jpg row is excluded
    assert all("GetApplicationAttachment" in u for u in urls)


def test_parse_exhibit_list_classifies() -> None:
    exhibits = parse_exhibit_list(EXHIBIT_HTML, base_url="https://apps.fcc.gov/x/View.cfm")
    types = {e.doc_type for e in exhibits}
    assert DocumentType.COVER_LETTER in types
    assert DocumentType.AUTHORIZATION_LETTER in types
    assert DocumentType.CONFIDENTIALITY_REQUEST in types


def test_classify_document() -> None:
    assert classify_document("Cover Letter") == DocumentType.COVER_LETTER
    assert classify_document("Letter of Authorization") == DocumentType.AUTHORIZATION_LETTER
    assert classify_document("Confidentiality Request") == DocumentType.CONFIDENTIALITY_REQUEST
    assert classify_document("SAR Attestation Statement") == DocumentType.ATTESTATION
    assert classify_document("Test Report") == DocumentType.OTHER

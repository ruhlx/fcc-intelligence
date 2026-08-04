"""Tests for the Stage 3 PDF extraction fallback pipeline."""

from __future__ import annotations

import app.parser.pdf_extractor as pe
from app.parser.pdf_extractor import extract_text

RICH = " ".join(["compliance"] * 40)


def test_uses_pdfplumber_when_good(monkeypatch) -> None:
    monkeypatch.setattr(pe, "_extract_pdfplumber", lambda data: RICH)
    monkeypatch.setattr(pe, "_extract_pymupdf", lambda data: "should not be used")
    result = extract_text(b"%PDF-fake")
    assert result.method == "pdfplumber"
    assert result.text == RICH


def test_falls_back_to_pymupdf(monkeypatch) -> None:
    monkeypatch.setattr(pe, "_extract_pdfplumber", lambda data: "too short")
    monkeypatch.setattr(pe, "_extract_pymupdf", lambda data: RICH)
    result = extract_text(b"%PDF-fake")
    assert result.method == "pymupdf"


def test_falls_back_to_ocr(monkeypatch) -> None:
    monkeypatch.setattr(pe, "_extract_pdfplumber", lambda data: "")
    monkeypatch.setattr(pe, "_extract_pymupdf", lambda data: "")
    monkeypatch.setattr(pe, "_extract_ocr", lambda data: RICH)
    result = extract_text(b"%PDF-fake")
    assert result.method == "ocr"


def test_ocr_can_be_disabled(monkeypatch) -> None:
    monkeypatch.setattr(pe, "_extract_pdfplumber", lambda data: "")
    monkeypatch.setattr(pe, "_extract_pymupdf", lambda data: "short text only")

    def _ocr_should_not_run(data):  # pragma: no cover - must not be called
        raise AssertionError("OCR should be disabled")

    monkeypatch.setattr(pe, "_extract_ocr", _ocr_should_not_run)
    result = extract_text(b"%PDF-fake", enable_ocr=False)
    # Returns the best (longest) available text even if poor.
    assert result.text == "short text only"


def test_handles_strategy_exception(monkeypatch) -> None:
    def _boom(data):
        raise RuntimeError("corrupt pdf")

    monkeypatch.setattr(pe, "_extract_pdfplumber", _boom)
    monkeypatch.setattr(pe, "_extract_pymupdf", lambda data: RICH)
    result = extract_text(b"%PDF-fake")
    assert result.method == "pymupdf"


def test_all_fail_returns_empty(monkeypatch) -> None:
    monkeypatch.setattr(pe, "_extract_pdfplumber", lambda data: "")
    monkeypatch.setattr(pe, "_extract_pymupdf", lambda data: "")
    monkeypatch.setattr(pe, "_extract_ocr", lambda data: "")
    result = extract_text(b"%PDF-fake")
    assert result.method == "none"
    assert result.text == ""

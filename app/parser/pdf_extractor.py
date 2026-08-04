"""Stage 3 — multi-strategy PDF text extraction.

Extraction pipeline, each step used only if the previous produced poor output:

  1. ``pdfplumber`` — best for born-digital text with layout.
  2. ``PyMuPDF`` (fitz) — faster/tolerant fallback for tricky encodings.
  3. OCR (``pytesseract`` on ``PyMuPDF``-rendered page images) — image-only PDFs.

Heavy libraries are imported lazily so the rest of the app (and its tests) can
run without them installed.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.logging_config import get_logger
from app.parser.text_cleaner import clean_text, is_extraction_poor

logger = get_logger(__name__)


@dataclass(frozen=True)
class ExtractionResult:
    """Result of a PDF text extraction attempt."""

    text: str
    method: str  # "pdfplumber" | "pymupdf" | "ocr" | "none"


def _extract_pdfplumber(data: bytes) -> str:
    import io

    import pdfplumber  # type: ignore[import-untyped]

    parts: list[str] = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
    return clean_text("\n".join(parts))


def _extract_pymupdf(data: bytes) -> str:
    import fitz  # type: ignore[import-untyped]

    parts: list[str] = []
    with fitz.open(stream=data, filetype="pdf") as doc:
        for page in doc:
            parts.append(page.get_text("text"))
    return clean_text("\n".join(parts))


def _extract_ocr(data: bytes, *, dpi: int = 200) -> str:
    import io

    import fitz  # type: ignore[import-untyped]
    import pytesseract  # type: ignore[import-untyped]
    from PIL import Image  # type: ignore[import-untyped]

    parts: list[str] = []
    with fitz.open(stream=data, filetype="pdf") as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=dpi)
            image = Image.open(io.BytesIO(pix.tobytes("png")))
            parts.append(pytesseract.image_to_string(image))
    return clean_text("\n".join(parts))


def extract_text(data: bytes, *, enable_ocr: bool = True) -> ExtractionResult:
    """Extract clean text from PDF ``data`` using the fallback pipeline.

    :param data: Raw PDF bytes.
    :param enable_ocr: Whether to attempt OCR when digital extraction fails.
    :returns: An :class:`ExtractionResult` with the text and the method used.
    """
    strategies: list[tuple[str, object]] = [
        ("pdfplumber", _extract_pdfplumber),
        ("pymupdf", _extract_pymupdf),
    ]
    if enable_ocr:
        strategies.append(("ocr", _extract_ocr))

    best = ExtractionResult(text="", method="none")
    for method, fn in strategies:
        try:
            text = fn(data)  # type: ignore[operator]
        except Exception as exc:  # broad: log and try the next strategy
            logger.warning("extraction_failed", method=method, error=str(exc))
            continue

        if len(text) > len(best.text):
            best = ExtractionResult(text=text, method=method)

        if not is_extraction_poor(text):
            logger.info("extraction_success", method=method, chars=len(text))
            return ExtractionResult(text=text, method=method)

    if not best.text:
        logger.warning("extraction_empty")
    return best

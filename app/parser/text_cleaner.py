"""Text normalisation and extraction-quality heuristics (Stage 3)."""

from __future__ import annotations

import re

# A page of real text has a high ratio of printable characters and a reasonable
# number of alphabetic words. Scanned/image-only PDFs yield almost nothing.
_WORD_RE = re.compile(r"[A-Za-z]{2,}")
_WHITESPACE_RE = re.compile(r"[ \t\xa0]+")
_MULTINEWLINE_RE = re.compile(r"\n{3,}")


def clean_text(raw: str) -> str:
    """Normalise whitespace and strip control characters from extracted text."""
    if not raw:
        return ""
    # Drop non-printable control chars except newline/tab.
    text = "".join(ch for ch in raw if ch == "\n" or ch == "\t" or ch.isprintable())
    text = _WHITESPACE_RE.sub(" ", text)
    text = _MULTINEWLINE_RE.sub("\n\n", text)
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(lines).strip()


def word_count(text: str) -> int:
    """Return the number of alphabetic words (length >= 2) in ``text``."""
    return len(_WORD_RE.findall(text))


def is_extraction_poor(text: str, *, min_words: int = 20) -> bool:
    """Return ``True`` when extracted text is too sparse to be trustworthy.

    Used to decide whether to fall back from pdfplumber to PyMuPDF, and from
    PyMuPDF to OCR.
    """
    return word_count(text) < min_words

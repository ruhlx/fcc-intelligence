"""PDF parsing package (Stage 3)."""

from app.parser.pdf_extractor import ExtractionResult, extract_text
from app.parser.text_cleaner import clean_text, is_extraction_poor, word_count

__all__ = [
    "ExtractionResult",
    "clean_text",
    "extract_text",
    "is_extraction_poor",
    "word_count",
]

"""Tests for Stage 3 text cleaning and quality heuristics."""

from __future__ import annotations

from app.parser.text_cleaner import clean_text, is_extraction_poor, word_count


def test_clean_text_collapses_whitespace_and_newlines() -> None:
    raw = "Hello    world\n\n\n\nfoo\tbar   "
    assert clean_text(raw) == "Hello world\n\nfoo bar"


def test_clean_text_strips_control_chars() -> None:
    raw = "abc\x00\x07def"
    assert clean_text(raw) == "abcdef"


def test_clean_text_empty() -> None:
    assert clean_text("") == ""


def test_word_count() -> None:
    assert word_count("The quick brown fox 12 !!") == 4


def test_is_extraction_poor_true_for_sparse() -> None:
    assert is_extraction_poor("just three words here") is True


def test_is_extraction_poor_false_for_rich() -> None:
    text = " ".join(["word"] * 40)
    assert is_extraction_poor(text) is False


def test_is_extraction_poor_custom_threshold() -> None:
    assert is_extraction_poor("one two three", min_words=2) is False

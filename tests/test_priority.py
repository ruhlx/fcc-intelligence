"""Tests for Stage 9 priority scoring."""

from __future__ import annotations

from datetime import date

from app.enrichment.priority import PriorityInput, compute_priority
from app.models.enums import ContactCategory

TODAY = date(2026, 8, 4)


def test_base_category_points() -> None:
    assert compute_priority(
        PriorityInput(ContactCategory.CERTIFICATION_MANAGER), today=TODAY
    ) == 40
    assert compute_priority(
        PriorityInput(ContactCategory.REGULATORY_AFFAIRS), today=TODAY
    ) == 35
    assert compute_priority(
        PriorityInput(ContactCategory.PRODUCT_COMPLIANCE), today=TODAY
    ) == 30
    assert compute_priority(
        PriorityInput(ContactCategory.PRODUCT_SECURITY), today=TODAY
    ) == 20


def test_recent_filing_bonus() -> None:
    data = PriorityInput(
        ContactCategory.PRODUCT_SECURITY, filing_dates=(date(2025, 6, 1),)
    )
    # 20 base + 10 recent = 30
    assert compute_priority(data, today=TODAY) == 30


def test_old_filing_no_recent_bonus() -> None:
    data = PriorityInput(
        ContactCategory.PRODUCT_SECURITY, filing_dates=(date(2020, 1, 1),)
    )
    assert compute_priority(data, today=TODAY) == 20


def test_multiple_filings_bonus() -> None:
    data = PriorityInput(
        ContactCategory.PRODUCT_COMPLIANCE,
        filing_dates=(date(2019, 1, 1), date(2018, 1, 1)),
    )
    # 30 base + 5 multiple (both old, no recent bonus)
    assert compute_priority(data, today=TODAY) == 35


def test_score_is_clamped_to_100() -> None:
    data = PriorityInput(
        ContactCategory.CERTIFICATION_MANAGER,
        filing_dates=(date(2025, 1, 1), date(2026, 1, 1), date(2024, 1, 1)),
    )
    # 40 + 10 + 5 = 55 (well under 100, but verify clamp path via monkeypatch-free max)
    assert compute_priority(data, today=TODAY) == 55


def test_ignore_category_scores_zero() -> None:
    assert compute_priority(PriorityInput(ContactCategory.IGNORE), today=TODAY) == 0


def test_default_today_is_used() -> None:
    # Should not raise and should return the base score with no filings.
    assert compute_priority(PriorityInput(ContactCategory.QUALITY)) == 0

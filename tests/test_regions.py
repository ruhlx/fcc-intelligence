"""Tests for the Europe country allowlist and region-string resolver."""

from __future__ import annotations

import pytest

from app.crawler.regions import EUROPE_COUNTRIES, is_european, resolve_region_filter


@pytest.mark.parametrize(
    ("country", "expected"),
    [
        ("Germany", True),
        ("Switzerland", True),
        ("United Kingdom", True),
        ("China", False),
        ("United States", False),
        (None, False),
        ("", False),
    ],
)
def test_is_european(country: str | None, expected: bool) -> None:
    assert is_european(country) is expected


def test_resolve_region_filter_europe() -> None:
    assert resolve_region_filter("europe") == EUROPE_COUNTRIES
    assert resolve_region_filter("Europe") == EUROPE_COUNTRIES  # case-insensitive


def test_resolve_region_filter_all_and_empty() -> None:
    assert resolve_region_filter("all") is None
    assert resolve_region_filter(None) is None
    assert resolve_region_filter("") is None


def test_resolve_region_filter_custom_list() -> None:
    assert resolve_region_filter("Germany, France") == frozenset({"Germany", "France"})

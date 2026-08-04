"""Tests for Stage 5 title classification."""

from __future__ import annotations

import pytest

from app.enrichment.classification import classify_title, is_saveable, normalise_title
from app.models.enums import ContactCategory


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Certification Manager", ContactCategory.CERTIFICATION_MANAGER),
        ("Global Type Approval Lead", ContactCategory.CERTIFICATION_MANAGER),
        ("Director of Regulatory Affairs", ContactCategory.REGULATORY_AFFAIRS),
        ("Product Compliance Engineer", ContactCategory.PRODUCT_COMPLIANCE),
        ("EMC Compliance Specialist", ContactCategory.PRODUCT_COMPLIANCE),
        ("Product Security Officer", ContactCategory.PRODUCT_SECURITY),
        ("Head of Cybersecurity", ContactCategory.PRODUCT_SECURITY),
        ("Quality Assurance Manager", ContactCategory.QUALITY),
        ("Chief Executive Officer", ContactCategory.EXECUTIVE),
        ("Senior RF Engineer", ContactCategory.ENGINEERING),
        ("Patent Attorney", ContactCategory.IGNORE),
        ("", ContactCategory.IGNORE),
        (None, ContactCategory.IGNORE),
    ],
)
def test_classify_title(title: str | None, expected: ContactCategory) -> None:
    assert classify_title(title) == expected


def test_certification_precedes_compliance() -> None:
    # "Certification" must win even when "compliance" is also present.
    assert classify_title("Certification & Compliance Manager") == (
        ContactCategory.CERTIFICATION_MANAGER
    )


def test_normalise_title_collapses_whitespace() -> None:
    assert normalise_title("  Product   Compliance\tManager ") == (
        "product compliance manager"
    )


@pytest.mark.parametrize(
    ("category", "saveable"),
    [
        (ContactCategory.CERTIFICATION_MANAGER, True),
        (ContactCategory.PRODUCT_COMPLIANCE, True),
        (ContactCategory.REGULATORY_AFFAIRS, True),
        (ContactCategory.PRODUCT_SECURITY, True),
        (ContactCategory.QUALITY, False),
        (ContactCategory.ENGINEERING, False),
        (ContactCategory.EXECUTIVE, False),
        (ContactCategory.IGNORE, False),
    ],
)
def test_is_saveable(category: ContactCategory, saveable: bool) -> None:
    assert is_saveable(category) is saveable

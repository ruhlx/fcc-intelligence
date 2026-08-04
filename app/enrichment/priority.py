"""Stage 9 - priority scoring for outbound sales prioritisation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from app.models.enums import ContactCategory

# Points awarded per category (Stage 9 spec).
_CATEGORY_POINTS: dict[ContactCategory, int] = {
    ContactCategory.CERTIFICATION_MANAGER: 40,
    ContactCategory.REGULATORY_AFFAIRS: 35,
    ContactCategory.PRODUCT_COMPLIANCE: 30,
    ContactCategory.PRODUCT_SECURITY: 20,
}

_RECENT_FILING_POINTS = 10
_MULTIPLE_FILINGS_POINTS = 5
_RECENT_WINDOW = timedelta(days=365 * 2)  # "recent" == within 2 years
_MAX_SCORE = 100


@dataclass(frozen=True)
class PriorityInput:
    """Inputs required to compute a contact's priority score."""

    category: ContactCategory
    filing_dates: tuple[date, ...] = ()

    @property
    def filing_count(self) -> int:
        return len(self.filing_dates)


def compute_priority(data: PriorityInput, *, today: date | None = None) -> int:
    """Compute a 0-100 priority score.

    Scoring:
      * category base points (Certification 40, Regulatory 35, Compliance 30,
        Security 20),
      * +10 if any linked filing is younger than two years,
      * +5 if the contact is linked to more than one filing.

    :param data: The contact's category and linked filing dates.
    :param today: Reference date (injectable for deterministic tests).
    :returns: An integer score clamped to ``[0, 100]``.
    """
    reference = today or date.today()
    score = _CATEGORY_POINTS.get(data.category, 0)

    if any((reference - fdate) <= _RECENT_WINDOW for fdate in data.filing_dates):
        score += _RECENT_FILING_POINTS

    if data.filing_count > 1:
        score += _MULTIPLE_FILINGS_POINTS

    return max(0, min(score, _MAX_SCORE))

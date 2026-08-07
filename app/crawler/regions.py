"""Country groupings used to filter discovery crawls (Stage 1, discovery mode).

FCC has no "search by region" field, so region filtering happens client-side
against the ``country`` column already captured in each result row (see
:func:`app.crawler.parsing.parse_search_results`). This list matches the exact
country-name spellings FCC's EAS uses; edit it to adjust the "Europe" filter.
"""

from __future__ import annotations

EUROPE_COUNTRIES: frozenset[str] = frozenset(
    {
        "Albania", "Andorra", "Austria", "Belarus", "Belgium",
        "Bosnia and Herzegovina", "Bulgaria", "Croatia", "Cyprus",
        "Czech Republic", "Czechia", "Denmark", "Estonia", "Finland",
        "France", "Germany", "Greece", "Hungary", "Iceland", "Ireland",
        "Italy", "Kosovo", "Latvia", "Liechtenstein", "Lithuania",
        "Luxembourg", "Malta", "Moldova", "Monaco", "Montenegro",
        "Netherlands", "North Macedonia", "Norway", "Poland", "Portugal",
        "Romania", "San Marino", "Serbia", "Slovakia", "Slovenia", "Spain",
        "Sweden", "Switzerland", "Ukraine", "United Kingdom", "Vatican City",
    }
)  # fmt: skip


def is_european(country: str | None) -> bool:
    """Return ``True`` if ``country`` (an FCC-style country name) is in Europe."""
    return bool(country) and country in EUROPE_COUNTRIES


def resolve_region_filter(value: str | None) -> frozenset[str] | None:
    """Resolve a region setting/request value to a country allowlist.

    ``"europe"`` -> :data:`EUROPE_COUNTRIES`; ``"all"``/empty -> ``None`` (no
    filter); anything else is treated as a comma-separated list of exact FCC
    country names, e.g. ``"Germany,France"``.
    """
    if not value or value.strip().lower() == "all":
        return None
    if value.strip().lower() == "europe":
        return EUROPE_COUNTRIES
    return frozenset(c.strip() for c in value.split(",") if c.strip())

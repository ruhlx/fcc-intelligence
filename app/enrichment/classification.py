"""Stage 5 — map a free-text job title to a :class:`ContactCategory`.

The classifier is deliberately rule-based (ordered keyword matching) so that it
is deterministic, fast, testable, and free of external dependencies. The LLM in
Stage 4 already proposes a category; this module is the authoritative,
auditable normalisation and the fallback when the LLM omits one.
"""

from __future__ import annotations

import re

from app.models.enums import ContactCategory

# Ordered (category, keyword) rules. The first matching rule wins, so more
# specific / higher-priority categories are listed first.
_RULES: tuple[tuple[ContactCategory, tuple[str, ...]], ...] = (
    (
        ContactCategory.CERTIFICATION_MANAGER,
        ("certification manager", "certification", "type approval", "homologation"),
    ),
    (
        ContactCategory.REGULATORY_AFFAIRS,
        ("regulatory affairs", "regulatory", "regulation", "government affairs"),
    ),
    (
        ContactCategory.PRODUCT_COMPLIANCE,
        ("product compliance", "compliance", "conformity", "emc"),
    ),
    (
        ContactCategory.PRODUCT_SECURITY,
        ("product security", "cybersecurity", "cyber security", "psirt", "security"),
    ),
    (
        ContactCategory.QUALITY,
        ("quality assurance", "quality", "qa manager"),
    ),
    (
        ContactCategory.EXECUTIVE,
        ("chief", "ceo", "cto", "coo", "president", "vice president", "vp ", "director"),
    ),
    (
        ContactCategory.ENGINEERING,
        ("engineer", "engineering", "r&d", "hardware", "firmware", "rf "),
    ),
)


def normalise_title(title: str | None) -> str:
    """Lower-case and collapse whitespace for robust keyword matching."""
    if not title:
        return ""
    return re.sub(r"\s+", " ", title).strip().lower()


def classify_title(title: str | None) -> ContactCategory:
    """Classify a job title into a :class:`ContactCategory`.

    :param title: Raw job title text, may be ``None``.
    :returns: The best-matching category, or ``IGNORE`` when nothing matches.
    """
    text = normalise_title(title)
    if not text:
        return ContactCategory.IGNORE
    for category, keywords in _RULES:
        if any(keyword in text for keyword in keywords):
            return category
    return ContactCategory.IGNORE


def is_saveable(category: ContactCategory) -> bool:
    """Return ``True`` if a contact in ``category`` should be persisted (Stage 5)."""
    return category in ContactCategory.saveable()

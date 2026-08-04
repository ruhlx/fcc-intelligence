"""Enrichment package: classification (Stage 5), dedup (Stage 6), priority (Stage 9)."""

from app.enrichment.classification import classify_title, is_saveable
from app.enrichment.dedup import CandidateContact, ContactDeduplicator, MergeResult
from app.enrichment.priority import PriorityInput, compute_priority

__all__ = [
    "CandidateContact",
    "ContactDeduplicator",
    "MergeResult",
    "PriorityInput",
    "classify_title",
    "compute_priority",
    "is_saveable",
]

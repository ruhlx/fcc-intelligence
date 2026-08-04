"""Selects the LLM extraction backend from configuration (Stage 4 / Stage 10)."""

from __future__ import annotations

from app.config import Settings, get_settings
from app.extractor.gemini_extractor import GeminiContactExtractor
from app.extractor.llm_extractor import ContactExtractor, OpenAIContactExtractor

_PROVIDERS = {"openai", "gemini"}


def build_extractor(settings: Settings | None = None) -> ContactExtractor:
    """Return the configured :class:`ContactExtractor` implementation.

    Controlled by ``LLM_PROVIDER`` (``"openai"`` or ``"gemini"``).

    :raises ValueError: if ``LLM_PROVIDER`` is not a recognised value.
    """
    settings = settings or get_settings()
    provider = settings.llm_provider.strip().lower()
    if provider == "gemini":
        return GeminiContactExtractor(settings)
    if provider == "openai":
        return OpenAIContactExtractor(settings)
    raise ValueError(
        f"Unknown LLM_PROVIDER {settings.llm_provider!r}; expected one of {sorted(_PROVIDERS)}"
    )

"""Stage 4 — structured contact extraction via the OpenAI Responses API.

A :class:`ContactExtractor` protocol decouples the pipeline from OpenAI so tests
(and offline runs) can inject a deterministic fake. The production
implementation uses the Responses API's structured-output parsing to guarantee
the model returns data conforming to :class:`ExtractionResponse`.
"""

from __future__ import annotations

from typing import Protocol

from app.config import Settings, get_settings
from app.extractor.schemas import ExtractionResponse
from app.logging_config import get_logger
from app.prompts.extraction import SYSTEM_PROMPT, build_user_prompt

logger = get_logger(__name__)


class ContactExtractor(Protocol):
    """Extracts structured contacts from raw document text."""

    def extract(
        self,
        *,
        document_text: str,
        document_type: str | None = None,
        company: str | None = None,
    ) -> ExtractionResponse:
        """Return the contacts found in ``document_text``."""
        ...


class OpenAIContactExtractor:
    """Concrete extractor backed by the OpenAI Responses API."""

    def __init__(self, settings: Settings | None = None, *, client: object | None = None):
        self._settings = settings or get_settings()
        self._client = client  # allow injection; created lazily otherwise

    def _get_client(self) -> object:
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(api_key=self._settings.openai_api_key)
        return self._client

    def extract(
        self,
        *,
        document_text: str,
        document_type: str | None = None,
        company: str | None = None,
    ) -> ExtractionResponse:
        """Call the Responses API and parse the structured result."""
        if not document_text.strip():
            return ExtractionResponse(contacts=[])

        client = self._get_client()
        user_prompt = build_user_prompt(
            document_text=document_text,
            document_type=document_type,
            company=company,
        )
        try:
            response = client.responses.parse(  # type: ignore[attr-defined]
                model=self._settings.openai_model,
                input=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                text_format=ExtractionResponse,
            )
            parsed = response.output_parsed
            result = parsed if isinstance(parsed, ExtractionResponse) else (
                ExtractionResponse.model_validate(parsed)
            )
        except Exception as exc:  # broad: surface as structured log + empty result
            logger.error("llm_extraction_error", error=str(exc), doc_type=document_type)
            return ExtractionResponse(contacts=[])

        logger.info(
            "llm_extraction_success",
            doc_type=document_type,
            contacts=len(result.contacts),
        )
        return result

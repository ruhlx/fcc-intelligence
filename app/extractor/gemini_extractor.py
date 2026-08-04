"""Stage 4 (alternative backend) — structured extraction via Google Gemini.

Implements the same :class:`~app.extractor.llm_extractor.ContactExtractor`
protocol as the OpenAI backend, so the pipeline is provider-agnostic. Gemini's
``response_schema`` returns JSON conforming to :class:`ExtractionResponse`.

The ``google-genai`` SDK is imported lazily (only when a client is actually
created), so tests can inject a fake client and run fully offline. The request
``config`` is passed as a plain ``dict`` for the same reason — no SDK types are
referenced at call time.
"""

from __future__ import annotations

from app.config import Settings, get_settings
from app.extractor.schemas import ExtractionResponse
from app.logging_config import get_logger
from app.prompts.extraction import SYSTEM_PROMPT, build_user_prompt

logger = get_logger(__name__)


class GeminiContactExtractor:
    """Concrete extractor backed by the Google Gemini API."""

    def __init__(self, settings: Settings | None = None, *, client: object | None = None):
        self._settings = settings or get_settings()
        self._client = client  # allow injection; created lazily otherwise

    def _get_client(self) -> object:
        if self._client is None:
            from google import genai  # type: ignore[attr-defined]

            self._client = genai.Client(api_key=self._settings.gemini_api_key)
        return self._client

    def extract(
        self,
        *,
        document_text: str,
        document_type: str | None = None,
        company: str | None = None,
    ) -> ExtractionResponse:
        """Call Gemini with a JSON schema and parse the structured result."""
        if not document_text.strip():
            return ExtractionResponse(contacts=[])

        client = self._get_client()
        user_prompt = build_user_prompt(
            document_text=document_text,
            document_type=document_type,
            company=company,
        )
        try:
            response = client.models.generate_content(  # type: ignore[attr-defined]
                model=self._settings.gemini_model,
                contents=user_prompt,
                config={
                    "system_instruction": SYSTEM_PROMPT,
                    "response_mime_type": "application/json",
                    "response_schema": ExtractionResponse,
                    "temperature": 0.0,
                },
            )
            result = self._parse(response)
        except Exception as exc:  # broad: surface as structured log + empty result
            logger.error("llm_extraction_error", error=str(exc), doc_type=document_type)
            return ExtractionResponse(contacts=[])

        logger.info(
            "llm_extraction_success",
            provider="gemini",
            doc_type=document_type,
            contacts=len(result.contacts),
        )
        return result

    @staticmethod
    def _parse(response: object) -> ExtractionResponse:
        """Turn a Gemini response into an :class:`ExtractionResponse`.

        Prefers the SDK's already-parsed object, falling back to the raw JSON
        ``text`` payload.
        """
        parsed = getattr(response, "parsed", None)
        if isinstance(parsed, ExtractionResponse):
            return parsed
        if parsed is not None:
            return ExtractionResponse.model_validate(parsed)
        text = getattr(response, "text", None)
        if text:
            return ExtractionResponse.model_validate_json(text)
        return ExtractionResponse(contacts=[])

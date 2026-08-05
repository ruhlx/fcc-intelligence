"""Tests for the Gemini extraction backend and provider selection."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.config import Settings
from app.extractor import (
    GeminiContactExtractor,
    OpenAIContactExtractor,
    build_extractor,
)
from app.extractor.schemas import GeminiContact, GeminiExtractionResponse


class _FakeModels:
    def __init__(self, response: object, *, raise_exc: Exception | None = None) -> None:
        self._response = response
        self._raise = raise_exc
        self.calls: list[dict] = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if self._raise is not None:
            raise self._raise
        return self._response


class _FakeClient:
    def __init__(self, models: _FakeModels) -> None:
        self.models = models


def _client(response: object, *, raise_exc: Exception | None = None) -> _FakeClient:
    return _FakeClient(_FakeModels(response, raise_exc=raise_exc))


def _gemini_contact(**kw: object) -> GeminiContact:
    base: dict[str, object] = dict(
        full_name="Jane Doe", email="JANE@x.com", phone=None, title="Certification Manager",
        company="x", document_type="COVER", is_internal_employee=True, confidence=80,
    )
    base.update(kw)
    return GeminiContact(**base)  # type: ignore[arg-type]


def test_gemini_extract_uses_parsed_object() -> None:
    parsed = GeminiExtractionResponse(contacts=[_gemini_contact()])
    client = _client(SimpleNamespace(parsed=parsed, text=None))
    extractor = GeminiContactExtractor(client=client)

    result = extractor.extract(document_text="text mentioning Jane", document_type="COVER")
    assert result.contacts[0].email == "jane@x.com"  # normalised to lowercase
    # Verify the request carried the no-default Gemini schema.
    cfg = client.models.calls[0]["config"]
    assert cfg["response_schema"] is GeminiExtractionResponse
    assert cfg["response_mime_type"] == "application/json"


def test_gemini_response_schema_has_no_defaults() -> None:
    """Regression guard: Gemini rejects any schema containing `default`."""

    def _no_default(node: object) -> bool:
        if isinstance(node, dict):
            if "default" in node:
                return False
            return all(_no_default(v) for v in node.values())
        if isinstance(node, list):
            return all(_no_default(v) for v in node)
        return True

    assert _no_default(GeminiExtractionResponse.model_json_schema())


def test_gemini_falls_back_to_text_json() -> None:
    payload = (
        '{"contacts": [{"full_name": "Bob", "email": null, "phone": null, '
        '"title": "QA", "company": "x", "document_type": "COVER", '
        '"is_internal_employee": true, "confidence": 40}]}'
    )
    client = _client(SimpleNamespace(parsed=None, text=payload))
    extractor = GeminiContactExtractor(client=client)
    result = extractor.extract(document_text="text mentioning Bob")
    assert result.contacts[0].full_name == "Bob"


def test_gemini_empty_text_short_circuits() -> None:
    client = _client(SimpleNamespace(parsed=None, text=None))
    extractor = GeminiContactExtractor(client=client)
    assert extractor.extract(document_text="  ").contacts == []
    assert client.models.calls == []


def test_gemini_error_returns_empty() -> None:
    client = _client(None, raise_exc=RuntimeError("quota exceeded"))
    extractor = GeminiContactExtractor(client=client)
    assert extractor.extract(document_text="meaningful text").contacts == []


def test_build_extractor_selects_provider() -> None:
    assert isinstance(build_extractor(Settings(llm_provider="gemini")), GeminiContactExtractor)
    assert isinstance(build_extractor(Settings(llm_provider="OpenAI")), OpenAIContactExtractor)


def test_build_extractor_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
        build_extractor(Settings(llm_provider="anthropic"))

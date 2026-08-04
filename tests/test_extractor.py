"""Tests for the Stage 4 LLM extractor (with a fake OpenAI client)."""

from __future__ import annotations

from types import SimpleNamespace

from app.extractor import ExtractedContact, ExtractionResponse, OpenAIContactExtractor


class _FakeResponses:
    def __init__(self, parsed: object, *, raise_exc: Exception | None = None) -> None:
        self._parsed = parsed
        self._raise = raise_exc
        self.calls: list[dict] = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        if self._raise is not None:
            raise self._raise
        return SimpleNamespace(output_parsed=self._parsed)


class _FakeClient:
    def __init__(self, responses: _FakeResponses) -> None:
        self.responses = responses


def test_extract_returns_parsed_contacts() -> None:
    parsed = ExtractionResponse(
        contacts=[
            ExtractedContact(
                full_name="Jane Doe",
                email="Jane.Doe@u-blox.com",
                title="Certification Manager",
                is_internal_employee=True,
                confidence=90,
            )
        ]
    )
    client = _FakeClient(_FakeResponses(parsed))
    extractor = OpenAIContactExtractor(client=client)

    result = extractor.extract(document_text="Signed by Jane Doe", document_type="COVER_LETTER")
    assert len(result.contacts) == 1
    # email normalised to lowercase by the schema validator.
    assert result.contacts[0].email == "jane.doe@u-blox.com"


def test_extract_empty_text_short_circuits() -> None:
    client = _FakeClient(_FakeResponses(None))
    extractor = OpenAIContactExtractor(client=client)
    result = extractor.extract(document_text="   ")
    assert result.contacts == []
    assert client.responses.calls == []  # LLM not called


def test_extract_handles_dict_parsed() -> None:
    parsed = {"contacts": [{"full_name": "Bob", "confidence": 50}]}
    client = _FakeClient(_FakeResponses(parsed))
    extractor = OpenAIContactExtractor(client=client)
    result = extractor.extract(document_text="text with Bob mentioned")
    assert result.contacts[0].full_name == "Bob"


def test_extract_error_returns_empty() -> None:
    client = _FakeClient(_FakeResponses(None, raise_exc=RuntimeError("api down")))
    extractor = OpenAIContactExtractor(client=client)
    result = extractor.extract(document_text="some meaningful text here")
    assert result.contacts == []

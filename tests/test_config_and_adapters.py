"""Tests for configuration and the source-adapter registry."""

from __future__ import annotations

from pathlib import Path

from app.config import Settings
from app.crawler.adapters import available_sources, get_adapter, register_adapter
from app.models.enums import ContactCategory, DocumentType


def test_settings_pdf_directory_and_ensure(tmp_path: Path) -> None:
    settings = Settings(data_directory=tmp_path)
    assert settings.pdf_directory == tmp_path / "pdfs"
    settings.ensure_directories()
    assert settings.pdf_directory.exists()


def test_settings_env_override(monkeypatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")
    settings = Settings()
    assert settings.log_level == "DEBUG"
    assert settings.openai_model == "gpt-test"


def test_saveable_categories() -> None:
    saveable = ContactCategory.saveable()
    assert ContactCategory.CERTIFICATION_MANAGER in saveable
    assert ContactCategory.ENGINEERING not in saveable


def test_adapter_registry_has_fcc() -> None:
    assert "fcc" in available_sources()
    assert get_adapter("fcc") is not None
    assert get_adapter("does-not-exist") is None


def test_register_new_adapter() -> None:
    class DummyAdapter:
        name = "dummy"

    register_adapter("dummy", DummyAdapter)
    assert "dummy" in available_sources()
    assert get_adapter("dummy") is DummyAdapter


def test_document_type_values_cover_stretch_sources() -> None:
    values = {d.value for d in DocumentType}
    for expected in ("CE_DOC", "TUV_CERTIFICATE", "UL_CERTIFICATE", "DEKRA_CERTIFICATE"):
        assert expected in values

"""Application configuration loaded from environment / .env (Stage 10)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings.

    Values are read from environment variables and an optional ``.env`` file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # LLM provider selection: "openai" or "gemini".
    llm_provider: str = Field(default="openai")

    # OpenAI
    openai_api_key: str = Field(default="", description="OpenAI API key.")
    openai_model: str = Field(default="gpt-4o-2024-08-06")

    # Google Gemini
    gemini_api_key: str = Field(default="", description="Google Gemini API key.")
    # `-latest` alias tracks the current flash model (avoids deprecation 404s).
    gemini_model: str = Field(default="gemini-flash-latest")

    # Database
    database_url: str = Field(
        default="postgresql+psycopg://fcc:fcc@localhost:5432/fcc",
        description="SQLAlchemy database URL.",
    )

    # Optional shared secret; when set, /ingest requires an X-Ingest-Token header.
    ingest_token: str = Field(default="")

    # Run `alembic upgrade head` on app startup (free-tier friendly; no paid
    # pre-deploy step needed). Off by default so tests and the CLI don't migrate.
    auto_migrate: bool = Field(default=False)

    @field_validator("database_url")
    @classmethod
    def _normalise_db_url(cls, value: str) -> str:
        """Coerce Render/Heroku-style URLs to the SQLAlchemy + psycopg3 driver.

        Providers hand out ``postgres://`` (or ``postgresql://``) URLs, which
        SQLAlchemy 2.0 cannot use directly with psycopg3. This rewrites them to
        ``postgresql+psycopg://`` so ``DATABASE_URL`` can be pasted verbatim.
        """
        for prefix in ("postgresql+psycopg://", "sqlite"):
            if value.startswith(prefix):
                return value
        if value.startswith("postgres://"):
            return "postgresql+psycopg://" + value.removeprefix("postgres://")
        if value.startswith("postgresql://"):
            return "postgresql+psycopg://" + value.removeprefix("postgresql://")
        return value

    # Storage
    data_directory: Path = Field(default=Path("./data"))

    # Logging
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="console", description="'console' or 'json'.")

    # API / CORS — comma-separated list of allowed browser origins for the SPA.
    cors_origins: str = Field(
        default="http://localhost:8080,http://localhost:5173,http://localhost:4173"
    )

    # Crawler / HTTP
    fcc_base_url: str = Field(default="https://apps.fcc.gov/oetcf/eas/reports")
    http_timeout: float = Field(default=30.0)
    http_max_retries: int = Field(default=3)
    crawl_concurrency: int = Field(default=4)
    # Cap filings processed per company in deep (--pdfs) mode — bounds PDF
    # downloads and LLM cost.
    fcc_max_filings: int = Field(default=10)
    # Cap in default (structured, no-LLM) mode. Higher because the 731 form
    # parse is free and fast — effectively "all filings" for most companies.
    fcc_max_filings_structured: int = Field(default=1000)
    # When False (default), only structured, freely-available contacts are
    # extracted (the 731 Responsible Party) — no PDF downloads, no LLM. When
    # True, exhibit PDFs are also downloaded and mined with the LLM.
    extract_pdfs: bool = Field(default=False)

    @property
    def pdf_directory(self) -> Path:
        """Directory where downloaded PDFs are stored."""
        return self.data_directory / "pdfs"

    @property
    def cors_origin_list(self) -> list[str]:
        """Parsed list of allowed CORS origins."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def ensure_directories(self) -> None:
        """Create data directories if they do not yet exist."""
        self.pdf_directory.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance (dependency-injection friendly)."""
    return Settings()

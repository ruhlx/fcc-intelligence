"""Pydantic schemas describing the LLM extraction contract (Stage 4)."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class ExtractedContact(BaseModel):
    """A single person extracted from a regulatory document."""

    full_name: str = Field(description="Person's full name.")
    email: str | None = Field(default=None, description="Email address if present.")
    phone: str | None = Field(default=None, description="Phone number if present.")
    title: str | None = Field(default=None, description="Job title / role.")
    company: str | None = Field(default=None, description="Employer the person works for.")
    document_type: str | None = Field(
        default=None, description="Type of document the person was found in."
    )
    is_internal_employee: bool = Field(
        default=True,
        description="True if an internal employee of the applicant, "
        "False for lawyers, test labs, or external consultants.",
    )
    confidence: int = Field(
        default=0, ge=0, le=100, description="Extraction confidence, 0-100."
    )

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().lower()
        return value or None

    @field_validator("full_name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        return value.strip()


class ExtractionResponse(BaseModel):
    """Top-level JSON object the model returns."""

    contacts: list[ExtractedContact] = Field(default_factory=list)

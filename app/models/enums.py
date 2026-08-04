"""Enumerations shared across the domain model."""

from __future__ import annotations

import enum


class ContactCategory(str, enum.Enum):
    """Normalised classification of a contact's job title (Stage 5)."""

    CERTIFICATION_MANAGER = "CERTIFICATION_MANAGER"
    PRODUCT_COMPLIANCE = "PRODUCT_COMPLIANCE"
    REGULATORY_AFFAIRS = "REGULATORY_AFFAIRS"
    PRODUCT_SECURITY = "PRODUCT_SECURITY"
    QUALITY = "QUALITY"
    ENGINEERING = "ENGINEERING"
    EXECUTIVE = "EXECUTIVE"
    IGNORE = "IGNORE"

    @classmethod
    def saveable(cls) -> frozenset[ContactCategory]:
        """Categories that are persisted as sales targets (Stage 5)."""
        return frozenset(
            {
                cls.CERTIFICATION_MANAGER,
                cls.PRODUCT_COMPLIANCE,
                cls.REGULATORY_AFFAIRS,
                cls.PRODUCT_SECURITY,
            }
        )


class DocumentType(str, enum.Enum):
    """The kind of exhibit attached to an FCC filing (Stage 2)."""

    AUTHORIZATION_LETTER = "AUTHORIZATION_LETTER"
    COVER_LETTER = "COVER_LETTER"
    CONFIDENTIALITY_REQUEST = "CONFIDENTIALITY_REQUEST"
    DECLARATION = "DECLARATION"
    ATTESTATION = "ATTESTATION"
    # Stretch-goal certificate types
    CE_DOC = "CE_DOC"
    TUV_CERTIFICATE = "TUV_CERTIFICATE"
    UL_CERTIFICATE = "UL_CERTIFICATE"
    SGS_CERTIFICATE = "SGS_CERTIFICATE"
    INTERTEK_CERTIFICATE = "INTERTEK_CERTIFICATE"
    EUROFINS_CERTIFICATE = "EUROFINS_CERTIFICATE"
    DEKRA_CERTIFICATE = "DEKRA_CERTIFICATE"
    OTHER = "OTHER"

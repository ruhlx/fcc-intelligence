"""Pluggable data-source adapters (stretch goal).

The pipeline is written against the FCC EAS, but the same
extract→parse→LLM→classify flow applies to other public certification
documents (CE Declarations of Conformity, TÜV, UL, SGS, Intertek, Eurofins,
DEKRA …). New sources implement :class:`SourceAdapter` and register themselves,
so the rest of the platform needs no changes to consume them.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.crawler.fcc_client import FccClient
from app.crawler.parsing import ApplicationRow, ExhibitRow
from app.models.enums import DocumentType


@runtime_checkable
class SourceAdapter(Protocol):
    """A source of regulatory documents for a given company."""

    #: Human-readable identifier, e.g. ``"fcc"`` or ``"tuv"``.
    name: str

    async def find_applications(self, company_name: str) -> list[ApplicationRow]:
        """Return the applications/filings for ``company_name``."""
        ...

    async def list_exhibits(self, app: ApplicationRow) -> list[ExhibitRow]:
        """Return the downloadable documents for one application."""
        ...


class FccAdapter:
    """Adapter for the FCC Equipment Authorization System (the default source)."""

    name = "fcc"

    def __init__(self, client: FccClient) -> None:
        # Imported here to avoid a circular import at module load time.
        from app.crawler.company_lookup import CompanyLookup
        from app.crawler.document_locator import DocumentLocator

        self._lookup = CompanyLookup(client)
        self._locator = DocumentLocator(client, pdf_directory=client._settings.pdf_directory)

    async def find_applications(self, company_name: str) -> list[ApplicationRow]:
        return await self._lookup.find_applications(company_name)

    async def list_exhibits(self, app: ApplicationRow) -> list[ExhibitRow]:
        return await self._locator.list_exhibits(app)


# --- Registry ---------------------------------------------------------------

_REGISTRY: dict[str, type] = {}

#: Certificate document types each stretch-goal source is expected to produce.
CERTIFICATE_SOURCE_TYPES: dict[str, DocumentType] = {
    "ce": DocumentType.CE_DOC,
    "tuv": DocumentType.TUV_CERTIFICATE,
    "ul": DocumentType.UL_CERTIFICATE,
    "sgs": DocumentType.SGS_CERTIFICATE,
    "intertek": DocumentType.INTERTEK_CERTIFICATE,
    "eurofins": DocumentType.EUROFINS_CERTIFICATE,
    "dekra": DocumentType.DEKRA_CERTIFICATE,
}


def register_adapter(name: str, adapter_cls: type) -> None:
    """Register a :class:`SourceAdapter` implementation under ``name``."""
    _REGISTRY[name] = adapter_cls


def get_adapter(name: str) -> type | None:
    """Return the registered adapter class for ``name`` (or ``None``)."""
    return _REGISTRY.get(name)


def available_sources() -> list[str]:
    """List the names of all registered adapters."""
    return sorted(_REGISTRY)


register_adapter("fcc", FccAdapter)

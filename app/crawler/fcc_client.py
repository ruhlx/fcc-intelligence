"""Low-level async HTTP client for the FCC EAS site.

Wraps ``httpx`` with retry/backoff (via ``tenacity``). It exposes only transport
concerns — fetching HTML and downloading binary attachments — while the calling
services own the URLs and parsing.
"""

from __future__ import annotations

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import Settings, get_settings
from app.logging_config import get_logger

logger = get_logger(__name__)

_USER_AGENT = (
    "fcc-intelligence/0.1 (+https://example.com; regulatory contact research)"
)


class FccClient:
    """Async client for fetching EAS pages and PDF attachments."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._own_client = client is None
        self._client = client or httpx.AsyncClient(
            timeout=self._settings.http_timeout,
            headers={"User-Agent": _USER_AGENT},
            follow_redirects=True,
        )

    @property
    def base_url(self) -> str:
        return self._settings.fcc_base_url

    async def __aenter__(self) -> FccClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the underlying client if this instance owns it."""
        if self._own_client:
            await self._client.aclose()

    def _retrying(self) -> AsyncRetrying:
        return AsyncRetrying(
            stop=stop_after_attempt(self._settings.http_max_retries),
            wait=wait_exponential(multiplier=0.5, max=8),
            retry=retry_if_exception_type(
                (httpx.TransportError, httpx.HTTPStatusError)
            ),
            reraise=True,
        )

    async def get_html(self, url: str, *, params: dict[str, str] | None = None) -> str:
        """GET a URL and return decoded text, retrying transient failures."""
        async for attempt in self._retrying():
            with attempt:
                resp = await self._client.get(url, params=params)
                resp.raise_for_status()
                return resp.text
        raise AssertionError("unreachable: reraise=True guarantees an exception or return")

    async def download(self, url: str) -> bytes:
        """Download a binary attachment (PDF), retrying transient failures."""
        async for attempt in self._retrying():
            with attempt:
                resp = await self._client.get(url)
                resp.raise_for_status()
                content = resp.content
                logger.info("pdf_downloaded", url=url, bytes=len(content))
                return content
        raise AssertionError("unreachable: reraise=True guarantees an exception or return")

"""Playwright (Firefox) fetcher that gets past FCC's Akamai Bot Manager.

FCC's Equipment Authorization site is protected by Akamai Bot Manager, which
returns 403/503 to plain HTTP clients (even with a spoofed TLS fingerprint)
because it requires a real browser to execute its JavaScript sensor. A headless
**Firefox** driven by Playwright passes it — Akamai's headless detection is
tuned mainly for Chrome, and Firefox still runs the sensor so the ``_abck``
cookie validates.

This fetcher launches one Firefox context per run and reuses it across the
search, exhibit and PDF-download requests (they share the validated session).

Requires the Playwright Firefox browser to be installed:

    poetry run playwright install firefox
"""

from __future__ import annotations

import contextlib
from typing import Any, Protocol

from app.config import Settings, get_settings
from app.logging_config import get_logger

logger = get_logger(__name__)

_FORM_TIMEOUT = 60_000
_LOAD_TIMEOUT = 45_000
_SUBMIT_SELECTOR = "input[type=submit], input[value='Search'], button[type=submit]"


class FccFetcher(Protocol):
    """Abstraction over "fetch FCC pages" so the crawler is browser-agnostic."""

    base_url: str

    async def search(self, company: str, *, show_records: int = 10) -> str:
        """Run the applicant-name search and return the result page HTML."""
        ...

    async def get_html(self, url: str) -> str:
        """Return the HTML at ``url`` within the authenticated session."""
        ...

    async def download(self, url: str, *, referer: str | None = None) -> bytes:
        """Download a binary attachment (PDF) within the session."""
        ...

    async def aclose(self) -> None:
        """Release browser resources."""
        ...


class BrowserFetcher:
    """Firefox-backed :class:`FccFetcher` (bypasses Akamai Bot Manager)."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self.base_url = f"{self._settings.fcc_base_url}"
        self._pw: Any = None
        self._browser: Any = None
        self._ctx: Any = None

    async def _ensure(self) -> None:
        if self._ctx is not None:
            return
        from playwright.async_api import async_playwright

        self._pw = await async_playwright().start()
        self._browser = await self._pw.firefox.launch(headless=True)
        self._ctx = await self._browser.new_context(accept_downloads=True)
        logger.info("browser_started", engine="firefox")

    async def search(self, company: str, *, show_records: int = 10) -> str:
        await self._ensure()
        page = await self._ctx.new_page()
        try:
            await page.goto(
                f"{self.base_url}/GenericSearch.cfm",
                wait_until="domcontentloaded",
                timeout=_FORM_TIMEOUT,
            )
            await page.fill("input[name=applicant_name]", company)
            await page.click(_SUBMIT_SELECTOR)
            await self._settle(page)

            # Enlarge the page via the results form's show_records/FromRec fields
            # to pull all filings in one request (bounded for safety).
            capped = max(10, min(show_records, 5000))
            if capped > 10 and await page.query_selector("input[name=next_value]"):
                await page.evaluate(
                    """(n) => {
                        const sr = document.querySelector('input[name=show_records]');
                        const fr = document.querySelector('input[name=FromRec]');
                        if (sr) sr.value = String(n);
                        if (fr) fr.value = '1';
                    }""",
                    capped,
                )
                await page.click("input[name=next_value]")
                await self._settle(page)

            html: str = await page.content()
            logger.info("fcc_search_done", company=company, rows=capped, bytes=len(html))
            return html
        finally:
            await page.close()

    async def get_html(self, url: str) -> str:
        await self._ensure()
        page = await self._ctx.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=_FORM_TIMEOUT)
            await self._settle(page)
            return str(await page.content())
        finally:
            await page.close()

    async def download(self, url: str, *, referer: str | None = None) -> bytes:
        await self._ensure()
        # Akamai requires the exhibit page as Referer for attachment downloads;
        # without it the endpoint returns 403 "not authorized".
        headers = {"Referer": referer} if referer else None
        resp = await self._ctx.request.get(url, headers=headers, timeout=_FORM_TIMEOUT)
        body: bytes = await resp.body()
        logger.info("pdf_downloaded", url=url, status=resp.status, bytes=len(body))
        return body

    async def aclose(self) -> None:
        if self._browser is not None:
            await self._browser.close()
        if self._pw is not None:
            await self._pw.stop()
        self._ctx = self._browser = self._pw = None

    @staticmethod
    async def _settle(page: Any) -> None:
        # networkidle can legitimately time out (long-polling assets); the DOM
        # content is already available, so suppress and continue.
        with contextlib.suppress(Exception):
            await page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)

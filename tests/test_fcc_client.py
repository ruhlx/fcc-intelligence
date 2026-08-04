"""Tests for the async FCC HTTP client (retry + transport via httpx MockTransport)."""

from __future__ import annotations

import httpx
import pytest

from app.config import Settings
from app.crawler.fcc_client import FccClient


def _client(handler) -> FccClient:
    transport = httpx.MockTransport(handler)
    http = httpx.AsyncClient(transport=transport)
    return FccClient(Settings(http_max_retries=3), client=http)


async def test_get_html_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>ok</html>")

    async with _client(handler) as client:
        assert await client.get_html("https://x/Search.cfm", params={"a": "b"}) == (
            "<html>ok</html>"
        )


async def test_download_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"%PDF-1.7")

    async with _client(handler) as client:
        assert await client.download("https://x/a.pdf") == b"%PDF-1.7"


async def test_retries_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.ConnectError("boom", request=request)
        return httpx.Response(200, text="recovered")

    async with _client(handler) as client:
        assert await client.get_html("https://x/Search.cfm") == "recovered"
    assert calls["n"] == 2


async def test_raises_on_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="server error")

    async with _client(handler) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_html("https://x/Search.cfm")


async def test_base_url_from_settings() -> None:
    client = FccClient(Settings(fcc_base_url="https://example.com/eas"))
    assert client.base_url == "https://example.com/eas"
    await client.aclose()

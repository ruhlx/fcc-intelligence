"""Tests for config DB-URL normalisation and the ingest endpoints/jobs."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services import jobs


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("postgres://u:p@h:5432/db", "postgresql+psycopg://u:p@h:5432/db"),
        ("postgresql://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
        ("postgresql+psycopg://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
        ("sqlite:///./x.db", "sqlite:///./x.db"),
    ],
)
def test_database_url_normalisation(given: str, expected: str) -> None:
    assert Settings(database_url=given).database_url == expected


def test_settings_for_overrides_provider_and_key() -> None:
    s = jobs.settings_for("gemini", "abc123")
    assert s.llm_provider == "gemini"
    assert s.gemini_api_key == "abc123"
    assert s.openai_api_key == ""  # unchanged


def test_settings_for_openai_key_routing() -> None:
    s = jobs.settings_for("openai", "sk-xyz")
    assert s.openai_api_key == "sk-xyz"


def test_settings_for_no_overrides_returns_base() -> None:
    s = jobs.settings_for(None, None)
    assert isinstance(s, Settings)


@pytest.fixture
def client(monkeypatch) -> TestClient:
    # Stub only the actual crawl/LLM/DB work, but keep the REAL start_job so the
    # endpoint's asyncio.create_task scheduling is exercised (regression guard:
    # a sync endpoint would raise "no running event loop" here).
    async def fake_run(job, provider, api_key):
        job.status = "completed"

    monkeypatch.setattr(jobs, "_run", fake_run)
    return TestClient(create_app())


def test_start_and_get_ingest_job(client: TestClient) -> None:
    resp = client.post("/ingest", json={"company": "u-blox", "provider": "gemini"})
    assert resp.status_code == 202
    body = resp.json()
    assert body["company"] == "u-blox"
    assert body["status"] in ("pending", "running", "completed")

    got = client.get(f"/ingest/{body['id']}")
    assert got.status_code == 200
    assert got.json()["id"] == body["id"]


def test_ingest_requires_company(client: TestClient) -> None:
    assert client.post("/ingest", json={"company": ""}).status_code == 422


def test_get_unknown_job_404(client: TestClient) -> None:
    assert client.get("/ingest/does-not-exist").status_code == 404


def test_ingest_token_enforced(monkeypatch) -> None:
    async def fake_run(job, provider, api_key):
        job.status = "completed"

    monkeypatch.setattr(jobs, "_run", fake_run)
    monkeypatch.setattr(
        "app.api.routes.ingest.get_settings", lambda: Settings(ingest_token="secret")
    )
    client = TestClient(create_app())
    assert client.post("/ingest", json={"company": "x"}).status_code == 401
    ok = client.post(
        "/ingest", json={"company": "x"}, headers={"X-Ingest-Token": "secret"}
    )
    assert ok.status_code == 202


def test_root_is_reachable(client: TestClient) -> None:
    # Root either serves the built SPA (200) or redirects to /docs (307/308),
    # depending on whether frontend/dist exists in the environment.
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code in (200, 307, 308)

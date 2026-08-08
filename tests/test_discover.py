"""Tests for the discovery job runner and /discover endpoints."""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services import jobs


@pytest.fixture
def client(monkeypatch) -> TestClient:
    # Stub only the actual crawl work, but keep the REAL start_discovery_job so
    # the endpoint's asyncio.create_task scheduling is exercised.
    async def fake_run_discovery(job, *, days, regions, extract_pdfs, max_filings):
        job.status = "completed"
        job.report = {"filings_scanned": 0, "companies_touched": 0}

    monkeypatch.setattr(jobs, "_run_discovery", fake_run_discovery)
    return TestClient(create_app())


def test_start_and_get_discovery_job(client: TestClient) -> None:
    resp = client.post("/discover", json={"regions": "europe", "days": 2})
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] in ("pending", "running", "completed")

    got = client.get(f"/discover/{body['id']}")
    assert got.status_code == 200
    assert got.json()["id"] == body["id"]


def test_discover_defaults_require_no_body_fields(client: TestClient) -> None:
    # Every field is optional — a bare {} should still start a job.
    resp = client.post("/discover", json={})
    assert resp.status_code == 202


def test_discover_unknown_job_404(client: TestClient) -> None:
    assert client.get("/discover/does-not-exist").status_code == 404


def test_discover_rejects_out_of_range_days(client: TestClient) -> None:
    assert client.post("/discover", json={"days": 0}).status_code == 422
    assert client.post("/discover", json={"days": 36501}).status_code == 422


def test_discover_accepts_multi_year_window(client: TestClient) -> None:
    # Not an FCC limit — confirm a large lookback (years) is accepted.
    resp = client.post("/discover", json={"days": 3650})
    assert resp.status_code == 202


async def test_start_discovery_job_creates_trackable_job(monkeypatch) -> None:
    async def fake_run_discovery(job, **_kwargs):
        job.status = "completed"

    monkeypatch.setattr(jobs, "_run_discovery", fake_run_discovery)
    job = jobs.start_discovery_job(regions="europe", days=5)
    assert job.company.startswith("discovery:")
    await asyncio.sleep(0)  # let the scheduled task run
    assert jobs.get_job(job.id) is job


async def test_auto_discover_loop_cancels_cleanly(monkeypatch) -> None:
    """The background scheduler task must stop on cancel, not hang."""
    started = asyncio.Event()
    real_sleep = asyncio.sleep

    async def fake_sleep(seconds: float) -> None:
        started.set()
        await real_sleep(3600)  # simulate the long wait we're about to cancel

    monkeypatch.setattr(jobs.asyncio, "sleep", fake_sleep)
    task = jobs.start_auto_discover_loop(1.0)
    await asyncio.wait_for(started.wait(), timeout=2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

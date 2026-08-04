"""Ingest endpoints — trigger and monitor the pipeline from the API/UI."""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.config import get_settings
from app.services.jobs import get_job, start_job

router = APIRouter(tags=["ingest"])


class IngestRequest(BaseModel):
    """Payload to kick off an ingestion run."""

    company: str = Field(min_length=1, description="Applicant / company name to crawl.")
    provider: str | None = Field(
        default=None, description="'openai' or 'gemini'; defaults to server config."
    )
    api_key: str | None = Field(
        default=None, description="LLM API key for this run (else uses server env)."
    )


class JobOut(BaseModel):
    """Job status response."""

    id: str
    company: str
    status: str
    created_at: str
    report: dict[str, object] | None = None
    error: str | None = None


def _check_token(token: str | None) -> None:
    configured = get_settings().ingest_token
    if configured and token != configured:
        raise HTTPException(status_code=401, detail="Invalid or missing ingest token")


@router.post("/ingest", response_model=JobOut, status_code=202)
def start_ingest(
    req: IngestRequest,
    x_ingest_token: str | None = Header(default=None),
) -> JobOut:
    """Start a background ingestion job and return its id immediately."""
    _check_token(x_ingest_token)
    job = start_job(req.company, provider=req.provider, api_key=req.api_key)
    return JobOut(**job.to_dict())


@router.get("/ingest/{job_id}", response_model=JobOut)
def get_ingest(job_id: str) -> JobOut:
    """Return the status (and, once finished, the report) of a job."""
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobOut(**job.to_dict())

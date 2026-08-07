"""Ingest endpoints — trigger and monitor the pipeline from the API/UI."""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.api.routes._job_common import JobOut, check_ingest_token
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
    extract_pdfs: bool = Field(
        default=False,
        description="Also download and LLM-mine exhibit PDFs (else 731 form only).",
    )
    max_filings: int | None = Field(
        default=None, ge=1, le=5000, description="Cap filings processed this run."
    )


@router.post("/ingest", response_model=JobOut, status_code=202)
async def start_ingest(
    req: IngestRequest,
    x_ingest_token: str | None = Header(default=None),
) -> JobOut:
    """Start a background ingestion job and return its id immediately.

    Must be ``async`` so ``start_job`` can schedule the work with
    ``asyncio.create_task`` on the running event loop (a sync endpoint would run
    in a threadpool with no loop and raise ``RuntimeError``).
    """
    check_ingest_token(x_ingest_token)
    job = start_job(
        req.company,
        provider=req.provider,
        api_key=req.api_key,
        extract_pdfs=req.extract_pdfs,
        max_filings=req.max_filings,
    )
    return JobOut(**job.to_dict())


@router.get("/ingest/{job_id}", response_model=JobOut)
def get_ingest(job_id: str) -> JobOut:
    """Return the status (and, once finished, the report) of a job."""
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobOut(**job.to_dict())

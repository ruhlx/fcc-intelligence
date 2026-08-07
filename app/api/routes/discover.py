"""Discovery endpoints — find filings/contacts by date range instead of company.

FCC has no "search by title" or "search by country" field; discovery instead
searches by grant-date window (applicant left blank) and filters the results to
a region client-side. Combined with the existing title/category classification,
this is how "find certification managers in Europe" works without naming
companies up front.
"""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.api.routes._job_common import JobOut, check_ingest_token
from app.services.jobs import get_job, start_discovery_job

router = APIRouter(tags=["discover"])


class DiscoverRequest(BaseModel):
    """Payload to kick off a date-range discovery run."""

    days: int | None = Field(
        default=None, ge=1, le=90, description="Lookback window in days (server default if unset)"
    )
    regions: str | None = Field(
        default=None,
        description="'europe' (default), 'all', or a comma-separated FCC country list.",
    )
    extract_pdfs: bool = Field(
        default=False,
        description="Also download and LLM-mine exhibit PDFs (else 731 form only).",
    )
    max_filings: int | None = Field(
        default=None, ge=1, le=2000, description="Cap matching filings processed."
    )


@router.post("/discover", response_model=JobOut, status_code=202)
async def start_discover(
    req: DiscoverRequest,
    x_ingest_token: str | None = Header(default=None),
) -> JobOut:
    """Start a background discovery job and return its id immediately."""
    check_ingest_token(x_ingest_token)
    job = start_discovery_job(
        days=req.days,
        regions=req.regions,
        extract_pdfs=req.extract_pdfs,
        max_filings=req.max_filings,
    )
    return JobOut(**job.to_dict())


@router.get("/discover/{job_id}", response_model=JobOut)
def get_discover(job_id: str) -> JobOut:
    """Return the status (and, once finished, the report) of a discovery job.

    Discovery jobs share the same in-memory job store as ``/ingest``, so this
    is equivalent to ``GET /ingest/{job_id}`` — provided as a matching path.
    """
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobOut(**job.to_dict())

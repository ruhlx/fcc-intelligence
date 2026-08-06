"""In-memory ingest-job registry and background runner.

Lets the pipeline be triggered from the API / UI ("enter a company, click Run")
instead of only the CLI. Jobs run as fire-and-forget asyncio tasks; state is
held in-process, which is correct for the single-worker deployment
(``WEB_CONCURRENCY=1``) this ships with.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime

from app.config import Settings, get_settings
from app.db.session import session_scope
from app.logging_config import get_logger
from app.services.factory import build_pipeline

logger = get_logger(__name__)


@dataclass
class IngestJob:
    """State of a single ingestion run."""

    id: str
    company: str
    status: str = "pending"  # pending | running | completed | failed
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    report: dict[str, object] | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


_JOBS: dict[str, IngestJob] = {}
_TASKS: set[asyncio.Task[None]] = set()


def create_job(company: str) -> IngestJob:
    """Register a new pending job for ``company``."""
    job = IngestJob(id=uuid.uuid4().hex, company=company)
    _JOBS[job.id] = job
    return job


def get_job(job_id: str) -> IngestJob | None:
    """Return a job by id, or ``None``."""
    return _JOBS.get(job_id)


def settings_for(
    provider: str | None, api_key: str | None, *, extract_pdfs: bool = False
) -> Settings:
    """Return settings with the request's provider / API key / mode overlaid.

    The base settings (and therefore ``DATABASE_URL``) are untouched; only the
    LLM provider, matching key, and PDF-extraction mode are overridden.
    """
    base = get_settings()
    updates: dict[str, object] = {}
    if provider:
        updates["llm_provider"] = provider
    effective = (provider or base.llm_provider).lower()
    if api_key:
        updates["gemini_api_key" if effective == "gemini" else "openai_api_key"] = api_key
    if extract_pdfs:
        updates["extract_pdfs"] = True
    return base.model_copy(update=updates) if updates else base


async def _run(
    job: IngestJob, provider: str | None, api_key: str | None, extract_pdfs: bool
) -> None:
    job.status = "running"
    logger.info("ingest_job_start", job_id=job.id, company=job.company, pdfs=extract_pdfs)
    try:
        settings = settings_for(provider, api_key, extract_pdfs=extract_pdfs)
        with session_scope() as session:
            pipeline = build_pipeline(session, settings=settings)
            report = await pipeline.run(job.company)
        job.report = {
            "applications": report.applications,
            "documents": report.documents,
            "contacts_created": report.contacts_created,
            "contacts_merged": report.contacts_merged,
            "errors": report.errors,
        }
        job.status = "completed"
        logger.info("ingest_job_done", job_id=job.id, **job.report)
    except Exception as exc:  # broad: record failure on the job, never crash the loop
        job.status = "failed"
        job.error = str(exc)
        logger.error("ingest_job_failed", job_id=job.id, error=str(exc))


def start_job(
    company: str,
    *,
    provider: str | None,
    api_key: str | None,
    extract_pdfs: bool = False,
) -> IngestJob:
    """Create a job and schedule it to run in the background."""
    job = create_job(company)
    task = asyncio.create_task(_run(job, provider, api_key, extract_pdfs))
    _TASKS.add(task)
    task.add_done_callback(_TASKS.discard)
    return job

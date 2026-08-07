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
    provider: str | None,
    api_key: str | None,
    *,
    extract_pdfs: bool = False,
    max_filings: int | None = None,
) -> Settings:
    """Return settings with the request's provider / API key / mode overlaid.

    The base settings (and therefore ``DATABASE_URL``) are untouched; only the
    LLM provider, matching key, PDF-extraction mode and per-run filing cap are
    overridden.
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
    if max_filings and max_filings > 0:
        updates["fcc_max_filings"] = max_filings
        updates["fcc_max_filings_structured"] = max_filings
    return base.model_copy(update=updates) if updates else base


async def _run(
    job: IngestJob,
    provider: str | None,
    api_key: str | None,
    extract_pdfs: bool,
    max_filings: int | None,
) -> None:
    job.status = "running"
    logger.info("ingest_job_start", job_id=job.id, company=job.company, pdfs=extract_pdfs)
    try:
        settings = settings_for(
            provider, api_key, extract_pdfs=extract_pdfs, max_filings=max_filings
        )
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
    max_filings: int | None = None,
) -> IngestJob:
    """Create a job and schedule it to run in the background."""
    job = create_job(company)
    task = asyncio.create_task(_run(job, provider, api_key, extract_pdfs, max_filings))
    _TASKS.add(task)
    task.add_done_callback(_TASKS.discard)
    return job


async def _run_discovery(
    job: IngestJob,
    *,
    days: int | None,
    regions: str | None,
    extract_pdfs: bool,
    max_filings: int | None,
) -> None:
    job.status = "running"
    logger.info("discovery_job_start", job_id=job.id, days=days, regions=regions)
    try:
        settings = settings_for(None, None, extract_pdfs=extract_pdfs)
        if days:
            settings = settings.model_copy(update={"discover_days": days})
        with session_scope() as session:
            pipeline = build_pipeline(session, settings=settings)
            report = await pipeline.run_discovery(regions=regions, max_filings=max_filings)
        job.report = {
            "date_from": str(report.date_from),
            "date_to": str(report.date_to),
            "regions": report.regions,
            "filings_scanned": report.filings_scanned,
            "companies_touched": report.companies_touched,
            "documents": report.documents,
            "contacts_created": report.contacts_created,
            "contacts_merged": report.contacts_merged,
            "errors": report.errors,
        }
        job.status = "completed"
        logger.info("discovery_job_done", job_id=job.id, **job.report)
    except Exception as exc:  # broad: record failure on the job, never crash the loop
        job.status = "failed"
        job.error = str(exc)
        logger.error("discovery_job_failed", job_id=job.id, error=str(exc))


def start_discovery_job(
    *,
    days: int | None = None,
    regions: str | None = None,
    extract_pdfs: bool = False,
    max_filings: int | None = None,
) -> IngestJob:
    """Create and schedule a date-range discovery job (no company named)."""
    label = f"discovery:{regions or 'default'}:{days or 'default'}d"
    job = create_job(label)
    task = asyncio.create_task(
        _run_discovery(
            job, days=days, regions=regions, extract_pdfs=extract_pdfs, max_filings=max_filings
        )
    )
    _TASKS.add(task)
    task.add_done_callback(_TASKS.discard)
    return job


async def _auto_discover_loop(interval_hours: float) -> None:
    """Run discovery on a fixed interval for as long as this process is up.

    This is an in-process asyncio loop, not OS-level cron: it only runs while
    the ``uvicorn`` process is alive, and its schedule resets on restart. One
    run is awaited to completion (via job-status polling) before the next is
    scheduled, so runs never overlap.
    """
    await asyncio.sleep(30)  # let the app finish booting first
    while True:
        try:
            job = start_discovery_job()
            while job.status in ("pending", "running"):
                await asyncio.sleep(5)
            logger.info("auto_discover_cycle_done", job_id=job.id, status=job.status)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # broad: one bad cycle must not kill the loop
            logger.error("auto_discover_cycle_failed", error=str(exc))
        await asyncio.sleep(max(interval_hours, 0.01) * 3600)


def start_auto_discover_loop(interval_hours: float) -> asyncio.Task[None]:
    """Schedule the in-process auto-discovery loop; call once at app startup."""
    return asyncio.create_task(_auto_discover_loop(interval_hours))

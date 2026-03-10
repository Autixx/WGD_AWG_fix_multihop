from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from onx.api.deps import get_database_session
from onx.core.config import get_settings
from onx.db.models.job import Job, JobState
from onx.db.models.job_lock import JobLock
from onx.schemas.common import HealthResponse, WorkerHealthResponse
from onx.workers.runtime_state import get_worker_runtime_state


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/health/worker", response_model=WorkerHealthResponse)
def worker_health(db: Session = Depends(get_database_session)) -> WorkerHealthResponse:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    runtime = get_worker_runtime_state().snapshot()

    def _count_jobs(state: JobState) -> int:
        value = db.scalar(select(func.count()).select_from(Job).where(Job.state == state))
        return int(value or 0)

    pending = _count_jobs(JobState.PENDING)
    running = _count_jobs(JobState.RUNNING)
    succeeded = _count_jobs(JobState.SUCCEEDED)
    failed = _count_jobs(JobState.FAILED)
    cancelled = _count_jobs(JobState.CANCELLED)
    dead = _count_jobs(JobState.DEAD)

    retry_scheduled = int(
        db.scalar(
            select(func.count())
            .select_from(Job)
            .where(
                Job.state == JobState.PENDING,
                Job.next_run_at.is_not(None),
                Job.next_run_at > now,
            )
        )
        or 0
    )
    expired_running_leases = int(
        db.scalar(
            select(func.count())
            .select_from(Job)
            .where(
                Job.state == JobState.RUNNING,
                Job.lease_expires_at.is_not(None),
                Job.lease_expires_at < now,
            )
        )
        or 0
    )

    locks_total = int(db.scalar(select(func.count()).select_from(JobLock)) or 0)
    locks_expired = int(
        db.scalar(
            select(func.count())
            .select_from(JobLock)
            .where(JobLock.expires_at < now)
        )
        or 0
    )

    return WorkerHealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        timestamp=now,
        worker=runtime,
        queue={
            "pending": pending,
            "running": running,
            "succeeded": succeeded,
            "failed": failed,
            "cancelled": cancelled,
            "dead": dead,
            "retry_scheduled": retry_scheduled,
            "expired_running_leases": expired_running_leases,
        },
        locks={
            "total": locks_total,
            "expired": locks_expired,
        },
    )

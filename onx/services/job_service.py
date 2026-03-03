from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from onx.db.models.event_log import EventLevel
from onx.db.models.job import Job, JobKind, JobState, JobTargetType
from onx.services.event_log_service import EventLogService


class JobService:
    def __init__(self) -> None:
        self._events = EventLogService()

    def create_job(
        self,
        db: Session,
        *,
        kind: JobKind,
        target_type: JobTargetType,
        target_id: str,
        request_payload: dict,
    ) -> Job:
        job = Job(
            kind=kind,
            target_type=target_type,
            target_id=target_id,
            state=JobState.PENDING,
            request_payload_json=request_payload,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        self._events.log(
            db,
            job_id=job.id,
            entity_type=target_type.value,
            entity_id=target_id,
            level=EventLevel.INFO,
            message=f"Job created: {kind.value}",
            details={"request_payload": request_payload},
        )
        return job

    def start_job(self, db: Session, job: Job, step: str | None = None) -> Job:
        job.state = JobState.RUNNING
        job.current_step = step
        job.started_at = datetime.now(timezone.utc)
        db.add(job)
        db.commit()
        db.refresh(job)
        self._events.log(
            db,
            job_id=job.id,
            entity_type=job.target_type.value,
            entity_id=job.target_id,
            level=EventLevel.INFO,
            message="Job started",
            details={"step": step},
        )
        return job

    def update_step(self, db: Session, job: Job, step: str) -> Job:
        job.current_step = step
        db.add(job)
        db.commit()
        db.refresh(job)
        self._events.log(
            db,
            job_id=job.id,
            entity_type=job.target_type.value,
            entity_id=job.target_id,
            level=EventLevel.INFO,
            message=step,
        )
        return job

    def succeed(self, db: Session, job: Job, result_payload: dict) -> Job:
        job.state = JobState.SUCCEEDED
        job.current_step = "completed"
        job.result_payload_json = result_payload
        job.error_text = None
        job.finished_at = datetime.now(timezone.utc)
        db.add(job)
        db.commit()
        db.refresh(job)
        self._events.log(
            db,
            job_id=job.id,
            entity_type=job.target_type.value,
            entity_id=job.target_id,
            level=EventLevel.INFO,
            message="Job succeeded",
            details={"result_payload": result_payload},
        )
        return job

    def fail(self, db: Session, job: Job, error_text: str, state: JobState = JobState.FAILED) -> Job:
        job.state = state
        job.error_text = error_text
        job.finished_at = datetime.now(timezone.utc)
        db.add(job)
        db.commit()
        db.refresh(job)
        self._events.log(
            db,
            job_id=job.id,
            entity_type=job.target_type.value,
            entity_id=job.target_id,
            level=EventLevel.ERROR,
            message="Job failed",
            details={"error": error_text, "state": state.value},
        )
        return job

    def list_jobs(self, db: Session) -> list[Job]:
        return list(db.scalars(select(Job).order_by(Job.created_at.desc())).all())

    def get_job(self, db: Session, job_id: str) -> Job | None:
        return db.get(Job, job_id)

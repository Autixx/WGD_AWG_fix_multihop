from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ONXBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class HealthResponse(ONXBaseModel):
    status: str
    service: str
    version: str
    timestamp: datetime


class WorkerRuntimeCounters(ONXBaseModel):
    poll_cycles_total: int
    jobs_claimed_total: int
    jobs_succeeded_total: int
    jobs_failed_total: int
    jobs_cancelled_total: int
    jobs_retried_total: int


class WorkerRuntimeRead(ONXBaseModel):
    running: bool
    worker_id: str | None
    poll_interval_seconds: int | None
    lease_seconds: int | None
    started_at: datetime | None
    stopped_at: datetime | None
    last_poll_started_at: datetime | None
    last_poll_finished_at: datetime | None
    last_job_claimed_at: datetime | None
    last_job_finished_at: datetime | None
    last_error_at: datetime | None
    last_error_message: str | None
    counters: WorkerRuntimeCounters


class WorkerQueueStats(ONXBaseModel):
    pending: int
    running: int
    succeeded: int
    failed: int
    cancelled: int
    dead: int
    retry_scheduled: int
    expired_running_leases: int


class WorkerLockStats(ONXBaseModel):
    total: int
    expired: int


class WorkerHealthResponse(ONXBaseModel):
    status: str
    service: str
    version: str
    timestamp: datetime
    worker: WorkerRuntimeRead
    queue: WorkerQueueStats
    locks: WorkerLockStats

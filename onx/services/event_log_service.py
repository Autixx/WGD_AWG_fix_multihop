from sqlalchemy import select
from sqlalchemy.orm import Session

from onx.db.models.event_log import EventLevel, EventLog


class EventLogService:
    def log(
        self,
        db: Session,
        *,
        entity_type: str,
        entity_id: str | None,
        message: str,
        level: EventLevel = EventLevel.INFO,
        job_id: str | None = None,
        details: dict | None = None,
    ) -> EventLog:
        event = EventLog(
            job_id=job_id,
            entity_type=entity_type,
            entity_id=entity_id,
            level=level,
            message=message,
            details_json=details,
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event

    def list_for_job(self, db: Session, job_id: str) -> list[EventLog]:
        return list(
            db.scalars(
                select(EventLog)
                .where(EventLog.job_id == job_id)
                .order_by(EventLog.created_at.asc())
            ).all()
        )

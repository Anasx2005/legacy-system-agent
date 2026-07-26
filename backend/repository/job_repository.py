from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.models.job import Job


def create_job(
    db: Session,
    system_id: int,
    phase: str,
    status: str,
) -> Job:

    job = Job(
        system_id=system_id,
        phase=phase,
        status=status,
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return job





def update_job_status(
    db: Session,
    job_id: int,
    status: str,
    error_message: str | None = None,
    finished_at: datetime | None = None,
) -> Job | None:

    statement = select(Job).where(Job.id == job_id)

    result = db.execute(statement)

    job = result.scalar_one_or_none()

    if job is None:
        return None

    if job.status == status and job.error_message == error_message and job.finished_at == finished_at:
        return job  # Already in target state — idempotent

    job.status = status
    job.error_message = error_message
    job.finished_at = finished_at

    db.commit()
    db.refresh(job)

    return job   
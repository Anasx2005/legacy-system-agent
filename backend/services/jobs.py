"""H2: durable background execution for Phase 1 ingestion jobs."""

from __future__ import annotations

import traceback
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import BackgroundTasks

from backend.database.session import SessionLocal
from backend.repository.job_repository import create_job, get_job, update_job_status
from backend.services.ingestion import run_as_is_ingestion


def enqueue_as_is_ingestion(
    *,
    background_tasks: BackgroundTasks,
    system_db_id: int,
    system_name: str,
    evidence_path: str | Path,
) -> tuple[int, str]:
    run_id = str(uuid.uuid4())
    with SessionLocal() as db:
        job = create_job(
            db,
            system_id=system_db_id,
            phase="as-is",
            status="queued",
            run_id=run_id,
        )
        job_id = job.id

    background_tasks.add_task(
        run_as_is_ingestion_job,
        job_id=job_id,
        system_name=system_name,
        evidence_path=str(evidence_path),
        run_id=run_id,
    )
    return job_id, run_id


def run_as_is_ingestion_job(
    *,
    job_id: int,
    system_name: str,
    evidence_path: str,
    run_id: str,
) -> None:
    """Always write a terminal status, even when a pipeline dependency fails."""
    with SessionLocal() as db:
        job = get_job(db, job_id)
        if job is None:
            return
        update_job_status(db, job_id, "running", started_at=datetime.now(UTC))

        try:
            run_as_is_ingestion(
                system_name,
                evidence_path,
                run_id=run_id,
                db=db,
            )
        except Exception as error:  # noqa: BLE001 - this is the job failure boundary
            update_job_status(
                db,
                job_id,
                "failed",
                error_message="".join(
                    traceback.format_exception_only(type(error), error)
                ).strip(),
                finished_at=datetime.now(UTC),
            )
            return

        update_job_status(db, job_id, "succeeded", finished_at=datetime.now(UTC))

"""H3 REST API for Phase 1 ingestion, jobs, and approved model data."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.api.dependencies import require_api_key
from backend.database.models.artifact_version import ArtifactVersion
from backend.database.models.job import Job
from backend.database.models.model_element_index import ModelElementIndex
from backend.database.session import get_db
from backend.repository.legacy_system_repository import get_legacy_system
from backend.services.ingestion import PipelineError, _validate_pipeline_scope
from backend.services.jobs import enqueue_as_is_ingestion
from backend.services.model_reader import read_model_element_from_main

router = APIRouter(dependencies=[Depends(require_api_key)])


class IngestRequest(BaseModel):
    evidence_path: str = Field(min_length=1)


@router.post("/systems/{system_id}/ingest", status_code=status.HTTP_202_ACCEPTED)
def ingest_system(
    system_id: int,
    request: IngestRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),  # noqa: B008 - FastAPI dependency declaration
) -> dict[str, object]:
    system = get_legacy_system(db, system_id)
    if system is None:
        raise HTTPException(status_code=404, detail="System not found.")
    try:
        _validate_pipeline_scope(system.name, request.evidence_path)
    except PipelineError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    job_id, run_id = enqueue_as_is_ingestion(
        background_tasks=background_tasks,
        system_db_id=system.id,
        system_name=system.name,
        evidence_path=Path(request.evidence_path),
    )
    return {"job_id": job_id, "run_id": run_id, "status": "queued"}


@router.get("/jobs/{job_id}")
def get_job_status(
    job_id: int,
    db: Session = Depends(get_db),  # noqa: B008 - FastAPI dependency declaration
) -> dict[str, object]:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return {
        "id": job.id,
        "system_id": job.system_id,
        "phase": job.phase,
        "status": job.status,
        "run_id": job.run_id,
        "error_message": job.error_message,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
    }


@router.get("/systems/{system_id}/elements")
def list_elements(
    system_id: int,
    layer: str | None = Query(default=None),
    db: Session = Depends(get_db),  # noqa: B008 - FastAPI dependency declaration
) -> list[dict[str, object]]:
    if get_legacy_system(db, system_id) is None:
        raise HTTPException(status_code=404, detail="System not found.")
    statement = select(ModelElementIndex).where(
        ModelElementIndex.system_id == system_id
    )
    if layer is not None:
        statement = statement.where(ModelElementIndex.layer == layer)
    elements = db.execute(statement.order_by(ModelElementIndex.name)).scalars().all()
    return [
        {
            "id": element.id,
            "layer": element.layer,
            "archimate_type": element.archimate_type,
            "name": element.name,
            "git_path": element.git_path,
            "current_commit": element.current_commit,
            "updated_at": element.updated_at,
        }
        for element in elements
    ]


@router.get("/elements/{element_id}")
def get_element_detail(
    element_id: int,
    db: Session = Depends(get_db),  # noqa: B008 - FastAPI dependency declaration
) -> dict[str, object]:
    element = db.get(ModelElementIndex, element_id)
    if element is None:
        raise HTTPException(status_code=404, detail="Element not found.")
    try:
        return read_model_element_from_main(element.git_path)
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail="Element file is not present on the model repository main branch.",
        ) from error
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.get("/systems/{system_id}/artifact-versions")
def list_artifact_versions(
    system_id: int,
    db: Session = Depends(get_db),  # noqa: B008 - FastAPI dependency declaration
) -> list[dict[str, object]]:
    if get_legacy_system(db, system_id) is None:
        raise HTTPException(status_code=404, detail="System not found.")
    versions = (
        db.execute(
            select(ArtifactVersion)
            .where(ArtifactVersion.system_id == system_id)
            .order_by(ArtifactVersion.created_at.desc())
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": version.id,
            "run_id": version.run_id,
            "commit_sha": version.commit_sha,
            "pr_number": version.pr_number,
            "approval_status": version.approval_status,
            "approved_by": version.approved_by,
            "approved_at": version.approved_at,
            "created_at": version.created_at,
        }
        for version in versions
    ]

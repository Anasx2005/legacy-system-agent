from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.models.artifact_version import ArtifactVersion


def create_artifact_version(
    db: Session,
    system_id: int,
    phase: str,
) -> ArtifactVersion:

    artifact = ArtifactVersion(
        system_id=system_id,
        phase=phase,
    )

    db.add(artifact)
    db.commit()
    db.refresh(artifact)

    return artifact



def update_artifact_version(
    db: Session,
    artifact_id: int,
    approval_status: str,
    approved_by: str | None = None,
    approved_at: datetime | None = None,
) -> ArtifactVersion | None:

    statement = select(ArtifactVersion).where(
        ArtifactVersion.id == artifact_id
    )

    result = db.execute(statement)

    artifact = result.scalar_one_or_none()

    if artifact is None:
        return None

    artifact.approval_status = approval_status
    artifact.approved_by = approved_by
    artifact.approved_at = approved_at

    db.commit()
    db.refresh(artifact)

    return artifact


def get_artifact_version_by_run(
    db: Session,
    system_id: int,
    run_id: str,
) -> ArtifactVersion | None:
    statement = select(ArtifactVersion).where(
        ArtifactVersion.system_id == system_id,
        ArtifactVersion.run_id == run_id,
    )

    return db.execute(statement).scalar_one_or_none()


def save_pending_artifact_version(
    db: Session,
    *,
    system_id: int,
    run_id: str,
    commit_sha: str,
    pr_number: int,
) -> ArtifactVersion:
    artifact = get_artifact_version_by_run(
        db=db,
        system_id=system_id,
        run_id=run_id,
    )

    if artifact is None:
        artifact = ArtifactVersion(
            system_id=system_id,
            phase="as-is",
            tag=f"pr-{pr_number}",
            author_type="agent",
            run_id=run_id,
            commit_sha=commit_sha,
            pr_number=pr_number,
            approval_status="pending",
            created_at=datetime.utcnow(),
        )
        db.add(artifact)

    else:
        artifact.phase = "as-is"
        artifact.tag = f"pr-{pr_number}"
        artifact.author_type = "agent"
        artifact.commit_sha = commit_sha
        artifact.pr_number = pr_number
        artifact.approval_status = "pending"

    db.commit()
    db.refresh(artifact)

    return artifact
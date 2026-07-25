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



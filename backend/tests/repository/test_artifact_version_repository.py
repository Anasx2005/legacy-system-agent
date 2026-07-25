from datetime import datetime, UTC

from backend.repository.artifact_version_repository import (
    create_artifact_version,
    update_artifact_version,
)

from backend.repository.legacy_system_repository import (
    create_legacy_system,
)




def test_create_artifact_version(db_session):
    system = create_legacy_system(
        db=db_session,
        name="ERP",
    )

    artifact = create_artifact_version(
        db=db_session,
        system_id=system.id,
        phase="ingestion",
    )

    assert artifact.id is not None
    assert artifact.system_id == system.id
    assert artifact.phase == "ingestion"




def test_update_artifact_version(db_session):
    system = create_legacy_system(
        db=db_session,
        name="ERP",
    )

    artifact = create_artifact_version(
        db=db_session,
        system_id=system.id,
        phase="analysis",
    )

    updated = update_artifact_version(
        db=db_session,
        artifact_id=artifact.id,
        approval_status="approved",
        approved_by="Anas",
        approved_at=datetime.now(UTC),
    )

    assert updated is not None
    assert updated.approval_status == "approved"
    assert updated.approved_by == "Anas"
    assert updated.approved_at is not None





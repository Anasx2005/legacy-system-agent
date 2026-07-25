from backend.repository.job_repository import (
    create_job,
    update_job_status,
)

from backend.repository.legacy_system_repository import (
    create_legacy_system,
)




def test_create_job(db_session):
    system = create_legacy_system(
        db=db_session,
        name="ERP",
    )

    job = create_job(
        db=db_session,
        system_id=system.id,
        phase="ingestion",
        status="running",
    )

    assert job.id is not None
    assert job.system_id == system.id
    assert job.phase == "ingestion"
    assert job.status == "running"



def test_update_job_status(db_session):
    system = create_legacy_system(
        db=db_session,
        name="ERP",
    )

    job = create_job(
        db=db_session,
        system_id=system.id,
        phase="analysis",
        status="running",
    )

    updated = update_job_status(
        db=db_session,
        job_id=job.id,
        status="completed",
    )

    assert updated is not None
    assert updated.status == "completed"

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from backend.api.ingestion import get_db
from backend.database.base import Base
from backend.database.models.artifact_version import ArtifactVersion
from backend.database.models.job import Job
from backend.database.models.legacy_system import LegacySystem
from backend.database.models.model_element_index import ModelElementIndex
from backend.main import app
from backend.services.ingestion import PipelineValidationError, run_as_is_ingestion
from backend.services.jobs import run_as_is_ingestion_job


@pytest.fixture
def session_factory(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'epic-h.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    try:
        yield factory
    finally:
        engine.dispose()


@pytest.fixture
def system(session_factory):
    with session_factory() as db:
        result = LegacySystem(name="legacy-system", description="test system")
        db.add(result)
        db.commit()
        db.refresh(result)
        return result.id


def configure_scope(monkeypatch, tmp_path):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    monkeypatch.setenv("EVIDENCE_DIR", str(evidence))
    monkeypatch.setenv("MODEL_SYSTEM_ID", "legacy-system")
    return evidence


def test_h1_validation_failure_never_reaches_git(
    monkeypatch, session_factory, system, tmp_path
):
    evidence = configure_scope(monkeypatch, tmp_path)
    monkeypatch.setattr(
        "backend.services.ingestion._run_parallel_analysts", lambda run_id: None
    )
    monkeypatch.setattr(
        "backend.services.ingestion._invoke_subagent", lambda name, run_id: None
    )
    monkeypatch.setattr("backend.services.ingestion.run_reconciler", lambda: None)
    monkeypatch.setattr(
        "backend.services.ingestion.run_validator",
        lambda: SimpleNamespace(overall_status="FAIL", error_count=2),
    )

    def git_must_not_run(*args, **kwargs):
        raise AssertionError("G1 must not run after validation failure")

    monkeypatch.setattr("backend.services.ingestion.commit_to_model", git_must_not_run)

    with session_factory() as db, pytest.raises(PipelineValidationError):
        run_as_is_ingestion("legacy-system", evidence, run_id="run-001", db=db)


def test_h1_runs_stages_in_order_and_opens_a_pr(
    monkeypatch, session_factory, system, tmp_path
):
    evidence = configure_scope(monkeypatch, tmp_path)
    events: list[str] = []
    monkeypatch.setattr(
        "backend.services.ingestion._run_parallel_analysts",
        lambda run_id: events.append("E1-E4"),
    )
    monkeypatch.setattr(
        "backend.services.ingestion._invoke_subagent",
        lambda name, run_id: events.append(name),
    )
    monkeypatch.setattr(
        "backend.services.ingestion.run_reconciler", lambda: events.append("F1")
    )
    monkeypatch.setattr(
        "backend.services.ingestion.run_validator",
        lambda: events.append("F2")
        or SimpleNamespace(overall_status="PASS", error_count=0),
    )
    monkeypatch.setattr(
        "backend.services.ingestion.commit_to_model",
        lambda system_id, run_id: events.append("G1")
        or SimpleNamespace(commit_sha="abc123"),
    )
    monkeypatch.setattr(
        "backend.services.ingestion.open_pull_request",
        lambda **kwargs: events.append("G2")
        or {"pr_number": 9, "pr_url": "https://example/pr/9"},
    )

    with session_factory() as db:
        result = run_as_is_ingestion(
            "legacy-system", evidence, run_id="run-success", db=db
        )

    assert events == ["E1-E4", "integration-mapper", "F1", "F2", "G1", "G2"]
    assert result.pr_number == 9


def test_h2_forced_exception_marks_job_failed(
    monkeypatch, session_factory, system, tmp_path
):
    configure_scope(monkeypatch, tmp_path)
    monkeypatch.setattr("backend.services.jobs.SessionLocal", session_factory)
    received_system_db_id: int | None = None

    def fail_pipeline(*args, **kwargs):
        nonlocal received_system_db_id
        received_system_db_id = kwargs["system_db_id"]
        raise RuntimeError("forced orchestrator failure")

    monkeypatch.setattr("backend.services.jobs.run_as_is_ingestion", fail_pipeline)
    with session_factory() as db:
        job = Job(system_id=system, phase="as-is", status="queued", run_id="run-002")
        db.add(job)
        db.commit()
        job_id = job.id

    run_as_is_ingestion_job(
        job_id=job_id,
        system_name="legacy-system",
        evidence_path="ignored-by-mock",
        run_id="run-002",
    )

    with session_factory() as db:
        job = db.get(Job, job_id)
        assert job.status == "failed"
        assert "forced orchestrator failure" in job.error_message
        assert job.finished_at is not None
    assert received_system_db_id == system


@pytest.fixture
def api_client(monkeypatch, session_factory, system):
    monkeypatch.setenv("API_KEY", "test-api-key")

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app), system
    finally:
        app.dependency_overrides.clear()


def test_h3_rejects_missing_api_key(api_client):
    client, system_id = api_client
    response = client.get(f"/systems/{system_id}/elements")
    assert response.status_code == 401


def test_h3_model_read_endpoints_and_errors(monkeypatch, api_client, session_factory):
    client, system_id = api_client
    with session_factory() as db:
        element = ModelElementIndex(
            system_id=system_id,
            layer="application",
            archimate_type="Application Component",
            name="Customer API",
            git_path="systems/legacy-system/as-is/application/customer-api.json",
            current_commit="abc123",
            updated_at=datetime.now(UTC),
        )
        db.add(element)
        db.add(
            ArtifactVersion(
                system_id=system_id,
                run_id="run-003",
                commit_sha="abc123",
                pr_number=7,
                approval_status="pending",
                created_at=datetime.now(UTC),
            )
        )
        db.add(
            Job(
                system_id=system_id, phase="as-is", status="succeeded", run_id="run-job"
            )
        )
        db.commit()
        element_id = element.id
        job_id = db.scalar(select(Job.id))

    headers = {"X-API-Key": "test-api-key"}
    listed = client.get(
        f"/systems/{system_id}/elements?layer=application", headers=headers
    )
    assert listed.status_code == 200
    assert listed.json()[0]["name"] == "Customer API"
    assert client.get("/systems/999/elements", headers=headers).status_code == 404

    monkeypatch.setattr(
        "backend.api.ingestion.read_model_element_from_main",
        lambda path: {
            "id": "customer-api",
            "evidence": [{"locator": "code/api.py#L1"}],
        },
    )
    detail = client.get(f"/elements/{element_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["id"] == "customer-api"
    assert client.get("/elements/999", headers=headers).status_code == 404

    versions = client.get(f"/systems/{system_id}/artifact-versions", headers=headers)
    assert versions.status_code == 200
    assert versions.json()[0]["pr_number"] == 7
    assert (
        client.get("/systems/999/artifact-versions", headers=headers).status_code == 404
    )

    job = client.get(f"/jobs/{job_id}", headers=headers)
    assert job.status_code == 200
    assert job.json()["status"] == "succeeded"
    assert client.get("/jobs/999", headers=headers).status_code == 404


def test_h3_ingest_returns_queued_job_and_checks_system(
    monkeypatch,
    api_client,
    tmp_path,
):
    client, system_id = api_client
    evidence = configure_scope(monkeypatch, tmp_path)
    monkeypatch.setattr(
        "backend.api.ingestion.enqueue_as_is_ingestion",
        lambda **kwargs: (55, "run-004"),
    )
    headers = {"X-API-Key": "test-api-key"}
    response = client.post(
        f"/systems/{system_id}/ingest",
        headers=headers,
        json={"evidence_path": str(evidence)},
    )
    assert response.status_code == 202
    assert response.json() == {"job_id": 55, "run_id": "run-004", "status": "queued"}
    assert (
        client.post(
            "/systems/999/ingest",
            headers=headers,
            json={"evidence_path": str(evidence)},
        ).status_code
        == 404
    )

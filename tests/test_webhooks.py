import hashlib
import hmac
import json
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from backend.api.webhooks import get_db
from backend.database.base import Base
from backend.database.models.artifact_version import ArtifactVersion
from backend.database.models.legacy_system import LegacySystem
from backend.database.models.model_element_index import ModelElementIndex
from backend.main import app


def signature(payload_bytes: bytes, secret: str) -> str:
    digest = hmac.new(
        secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()
    return f"sha256={digest}"


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def webhook_db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'webhook-test.db'}")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield session_factory
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def git(args: list[str], cwd: Path) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture
def model_repo(tmp_path) -> Path:
    remote = tmp_path / "model-origin.git"
    checkout = tmp_path / "model-checkout"
    git(["init", "--bare", str(remote)], tmp_path)
    git(["clone", str(remote), str(checkout)], tmp_path)
    git(["checkout", "-b", "main"], checkout)
    git(["config", "user.name", "Webhook Test"], checkout)
    git(["config", "user.email", "webhook@example.com"], checkout)

    element_path = checkout / "systems" / "legacy-system" / "as-is" / "application"
    element_path.mkdir(parents=True)
    (element_path / "customer-api.json").write_text(
        json.dumps(
            {
                "id": "customer-api",
                "layer": "application",
                "archimate_type": "Application Component",
                "name": "Customer API",
            }
        ),
        encoding="utf-8",
    )
    git(["add", "."], checkout)
    git(["commit", "-m", "Merged model update"], checkout)
    git(["push", "-u", "origin", "main"], checkout)
    return checkout


def test_rejects_webhook_when_secret_is_missing(client, monkeypatch):
    monkeypatch.delenv("GITHUB_WEBHOOK_SECRET", raising=False)
    response = client.post(
        "/webhooks/github",
        content=b"{}",
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": "sha256=invalid",
        },
    )
    assert response.status_code == 401


def test_rejects_webhook_with_invalid_signature(client, monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "test-secret")
    payload = json.dumps({}).encode("utf-8")
    response = client.post(
        "/webhooks/github",
        content=payload,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": "sha256=wrong-signature",
        },
    )
    assert response.status_code == 401


def test_merged_pr_approves_artifact_refreshes_index_and_ignores_redelivery(
    client,
    webhook_db,
    model_repo,
    monkeypatch,
):
    secret = "test-secret"
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", secret)
    monkeypatch.setenv("GITHUB_MODEL_REPO", "example/legacy-system-model")
    monkeypatch.setenv("MODEL_REPO_DIR", str(model_repo))
    monkeypatch.setenv("MODEL_SYSTEM_ID", "legacy-system")

    with webhook_db() as db:
        system = LegacySystem(name="legacy-system")
        db.add(system)
        db.flush()
        db.add(
            ArtifactVersion(
                system_id=system.id,
                run_id="run-001",
                commit_sha="feature-commit",
                pr_number=42,
                approval_status="pending",
            )
        )
        db.commit()

    main_commit = git(["rev-parse", "origin/main"], model_repo)
    payload = {
        "action": "closed",
        "number": 42,
        "repository": {"full_name": "example/legacy-system-model"},
        "pull_request": {
            "merged": True,
            "merge_commit_sha": main_commit,
            "merged_by": {"login": "reviewer"},
        },
    }
    raw_payload = json.dumps(payload).encode("utf-8")
    headers = {
        "X-GitHub-Event": "pull_request",
        "X-GitHub-Delivery": "delivery-001",
        "X-Hub-Signature-256": signature(raw_payload, secret),
    }

    response = client.post("/webhooks/github", content=raw_payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert response.json()["indexed_elements"] == 1

    with webhook_db() as db:
        artifact = db.scalar(
            select(ArtifactVersion).where(ArtifactVersion.pr_number == 42)
        )
        index = db.scalar(select(ModelElementIndex))
        assert artifact.approval_status == "approved"
        assert artifact.approved_by == "reviewer"
        assert index.name == "Customer API"
        assert index.git_path.endswith("application/customer-api.json")
        assert index.current_commit == main_commit

    duplicate = client.post("/webhooks/github", content=raw_payload, headers=headers)
    assert duplicate.status_code == 200
    assert duplicate.json()["status"] == "already_processed"

    with webhook_db() as db:
        assert db.query(ModelElementIndex).count() == 1

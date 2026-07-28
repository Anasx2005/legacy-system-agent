"""Unit tests for Git versioning and PR automation (Epic G1 & G2)."""

import os
import subprocess
from pathlib import Path
import pytest

from agents.git_versioning import commit_to_model, open_pull_request, _sanitize_string


def test_sanitize_string_masks_secret():
    secret = "ghp_secret_12345"
    message = f"Error connecting with token {secret} to repo"
    sanitized = _sanitize_string(message, secret)

    assert secret not in sanitized
    assert "***SECRET_TOKEN***" in sanitized


def test_commit_to_model_creates_branch_and_commits(tmp_path, monkeypatch):
    # Setup temporary git repository
    repo_dir = tmp_path / "model-repo"
    repo_dir.mkdir()

    subprocess.run(["git", "init"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True)

    # Initial commit on main
    (repo_dir / "README.md").write_text("# Model Repo\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], cwd=repo_dir, check=True)

    # Create target directory for model JSONs
    as_is_dir = repo_dir / "systems" / "test-sys" / "as-is" / "application"
    as_is_dir.mkdir(parents=True)
    (as_is_dir / "payment-service.json").write_text('{"id": "payment-service"}', encoding="utf-8")

    monkeypatch.setenv("MODEL_REPO_DIR", str(repo_dir))

    res = commit_to_model(system_id="test-sys", run_id="run-001", repo_dir=repo_dir)

    assert res["status"] == "success"
    assert res["branch"] == "feature/ingest-test-sys-run-001"
    assert res["commit_sha"] is not None

    # Check git branch
    branches = subprocess.run(["git", "branch", "--list"], cwd=repo_dir, capture_output=True, text=True).stdout
    assert "feature/ingest-test-sys-run-001" in branches


def test_commit_to_model_idempotent_when_no_staged_changes(tmp_path, monkeypatch):
    repo_dir = tmp_path / "model-repo"
    repo_dir.mkdir()

    subprocess.run(["git", "init"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True)

    (repo_dir / "README.md").write_text("# Model Repo\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], cwd=repo_dir, check=True)

    monkeypatch.setenv("MODEL_REPO_DIR", str(repo_dir))

    # Calling commit_to_model when nothing is changed
    res = commit_to_model(system_id="test-sys", run_id="run-002", repo_dir=repo_dir)

    assert res["status"] == "no_changes"
    assert res["branch"] == "feature/ingest-test-sys-run-002"


def test_open_pull_request_requires_token(tmp_path, monkeypatch):
    monkeypatch.setenv("MODEL_REPO_DIR", str(tmp_path))
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_MODEL_REPO", raising=False)

    with pytest.raises(RuntimeError, match="GITHUB_TOKEN and GITHUB_MODEL_REPO are required"):
        open_pull_request(system_id="test-sys", run_id="run-001", repo_dir=tmp_path)

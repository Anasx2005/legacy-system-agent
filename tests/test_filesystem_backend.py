from pathlib import Path

from deepagents.middleware.filesystem import _check_fs_permission

from agents.filesystem_backend import (
    agent_filesystem_permissions,
    create_agent_backend,
)


def test_evidence_route_can_read_glob_and_grep(monkeypatch, tmp_path):
    evidence_directory = tmp_path / "evidence"
    model_repository_directory = tmp_path / "model-repo"

    evidence_directory.mkdir()
    model_repository_directory.mkdir()
    (model_repository_directory / ".git").mkdir()
    (model_repository_directory / "systems").mkdir()

    evidence_file = evidence_directory / "legacy_code.txt"
    evidence_file.write_text(
        "Customer Portal calls the Customer API.",
        encoding="utf-8",
    )

    monkeypatch.setenv("EVIDENCE_DIR", str(evidence_directory))
    monkeypatch.setenv("MODEL_REPO_DIR", str(model_repository_directory))

    backend = create_agent_backend()

    read_result = backend.read("/evidence/legacy_code.txt")
    assert read_result.error is None
    assert read_result.file_data["content"] == "Customer Portal calls the Customer API."

    glob_result = backend.glob("*.txt", "/evidence/")
    assert glob_result.error is None
    assert any(match["path"] == "/evidence/legacy_code.txt" for match in glob_result.matches)

    grep_result = backend.grep("Customer API", "/evidence/")
    assert grep_result.error is None
    assert any(match["path"] == "/evidence/legacy_code.txt" for match in grep_result.matches)


def test_evidence_writes_are_denied_by_agent_permissions():
    permissions = agent_filesystem_permissions()

    result = _check_fs_permission(
        permissions,
        operation="write",
        path="/evidence/should-not-exist.txt",
    )

    assert result == "deny"


def test_systems_writes_are_allowed_and_reach_git_checkout(monkeypatch, tmp_path):
    evidence_directory = tmp_path / "evidence"
    model_repository_directory = tmp_path / "model-repo"

    evidence_directory.mkdir()
    model_repository_directory.mkdir()
    (model_repository_directory / ".git").mkdir()
    (model_repository_directory / "systems").mkdir()

    monkeypatch.setenv("EVIDENCE_DIR", str(evidence_directory))
    monkeypatch.setenv("MODEL_REPO_DIR", str(model_repository_directory))

    backend = create_agent_backend()

    output_path = "/systems/legacy-system/as-is/application/customer-portal.md"
    write_result = backend.write(output_path, "# Customer Portal\n")

    assert write_result.error is None

    real_output_file = (
        model_repository_directory
        / "systems"
        / "legacy-system"
        / "as-is"
        / "application"
        / "customer-portal.md"
    )
    assert real_output_file.read_text(encoding="utf-8") == "# Customer Portal\n"
import json

from agents.scoped_element_writers import create_technology_element_writer


def test_technology_writer_canonicalizes_a_bare_evidence_filename(
    monkeypatch, tmp_path
):
    evidence_directory = tmp_path / "evidence"
    model_repository_directory = tmp_path / "model-repo"
    (evidence_directory / "infra").mkdir(parents=True)
    (model_repository_directory / "systems").mkdir(parents=True)
    (evidence_directory / "infra" / "main.tf").write_text(
        'resource "aws_instance" "portal" {}\n', encoding="utf-8"
    )

    monkeypatch.setenv("EVIDENCE_DIR", str(evidence_directory))
    monkeypatch.setenv("MODEL_REPO_DIR", str(model_repository_directory))
    monkeypatch.setenv("MODEL_SYSTEM_ID", "legacy-system")

    result = create_technology_element_writer().invoke(
        {
            "id": "customer-portal-instance",
            "layer": "technology",
            "archimate_type": "Node",
            "name": "Customer Portal Instance",
            "documentation": "Terraform-managed portal instance.",
            "confidence": "observed",
            "evidence": [
                {"source_type": "terraform", "locator": "main.tf#L1-L1"}
            ],
            "relationships": [],
        }
    )

    assert result == "Validated element written: customer-portal-instance.json"
    output = model_repository_directory / "systems" / "legacy-system" / "as-is" / "technology" / "customer-portal-instance.json"
    assert json.loads(output.read_text(encoding="utf-8"))["evidence"][0]["locator"] == "infra/main.tf#L1-L1"


def test_technology_writer_skips_a_nonexistent_evidence_file(monkeypatch, tmp_path):
    evidence_directory = tmp_path / "evidence"
    model_repository_directory = tmp_path / "model-repo"
    (evidence_directory / "infra").mkdir(parents=True)
    (model_repository_directory / "systems").mkdir(parents=True)
    monkeypatch.setenv("EVIDENCE_DIR", str(evidence_directory))
    monkeypatch.setenv("MODEL_REPO_DIR", str(model_repository_directory))

    result = create_technology_element_writer().invoke(
        {
            "id": "invalid-infrastructure-candidate",
            "layer": "technology",
            "archimate_type": "Node",
            "name": "Invalid candidate",
            "documentation": "Must not be written.",
            "confidence": "inferred",
            "evidence": [{"source_type": "terraform", "locator": "infra/path#L1-L4"}],
            "relationships": [],
        }
    )

    assert result.startswith("Element skipped: Evidence file does not exist")
    assert not list(model_repository_directory.rglob("invalid-infrastructure-candidate.json"))

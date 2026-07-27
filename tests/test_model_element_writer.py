from agents.model_element_writer import persist_strategy_element
from agents.schema import ModelElement


def valid_strategy_element() -> ModelElement:
    return ModelElement(
        id="customer-self-service",
        layer="strategy",
        archimate_type="Course of Action",
        name="Customer Self-Service",
        documentation="An approach to improve customer self-service.",
        confidence="observed",
        evidence=[
            {
                "source_type": "strategy_document",
                "locator": "strategy/modernisation-plan.md#Customer self-service",
            }
        ],
        relationships=[],
    )


def test_writer_creates_json_in_the_model_repository(monkeypatch, tmp_path):
    evidence_directory = tmp_path / "evidence"
    model_repository_directory = tmp_path / "model-repo"

    (evidence_directory / "strategy").mkdir(parents=True)
    (evidence_directory / "motivation").mkdir(parents=True)
    (model_repository_directory / ".git").mkdir(parents=True)
    (model_repository_directory / "systems").mkdir()

    (evidence_directory / "strategy" / "modernisation-plan.md").write_text(
        "# Customer self-service\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("EVIDENCE_DIR", str(evidence_directory))
    monkeypatch.setenv("MODEL_REPO_DIR", str(model_repository_directory))
    monkeypatch.setenv("MODEL_SYSTEM_ID", "legacy-system")

    output_file = persist_strategy_element(valid_strategy_element())

    assert output_file.is_file()
    assert output_file.name == "customer-self-service.json"
    assert '"archimate_type": "Course of Action"' in output_file.read_text(
        encoding="utf-8"
    )


def test_writer_rejects_missing_evidence_file(monkeypatch, tmp_path):
    evidence_directory = tmp_path / "evidence"
    model_repository_directory = tmp_path / "model-repo"

    (evidence_directory / "strategy").mkdir(parents=True)
    (evidence_directory / "motivation").mkdir(parents=True)
    (model_repository_directory / ".git").mkdir(parents=True)
    (model_repository_directory / "systems").mkdir()

    monkeypatch.setenv("EVIDENCE_DIR", str(evidence_directory))
    monkeypatch.setenv("MODEL_REPO_DIR", str(model_repository_directory))

    element = valid_strategy_element()

    try:
        persist_strategy_element(element)
    except ValueError as error:
        assert "Evidence file does not exist" in str(error)
    else:
        raise AssertionError("Expected a missing evidence file to be rejected.")
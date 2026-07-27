from agents.model_element_writer import persist_business_element
from agents.schema import ModelElement


def valid_business_element() -> ModelElement:
    return ModelElement(
        id="customer-support-agent",
        layer="business",
        archimate_type="Business Actor",
        name="Customer Support Agent",
        documentation="A support agent who handles customer account enquiries.",
        confidence="observed",
        evidence=[
            {
                "source_type": "interview_transcript",
                "locator": (
                    "business/customer-support-interview.md#Participants"
                ),
            }
        ],
        relationships=[],
    )


def test_business_writer_creates_json_in_business_layer(monkeypatch, tmp_path):
    evidence_directory = tmp_path / "evidence"
    model_repository_directory = tmp_path / "model-repo"

    (evidence_directory / "business").mkdir(parents=True)
    (model_repository_directory / ".git").mkdir(parents=True)
    (model_repository_directory / "systems").mkdir()

    (evidence_directory / "business" / "customer-support-interview.md").write_text(
        "# Participants\nCustomer Support Agents handle enquiries.",
        encoding="utf-8",
    )

    monkeypatch.setenv("EVIDENCE_DIR", str(evidence_directory))
    monkeypatch.setenv("MODEL_REPO_DIR", str(model_repository_directory))
    monkeypatch.setenv("MODEL_SYSTEM_ID", "legacy-system")

    output_file = persist_business_element(valid_business_element())

    assert output_file.is_file()
    assert output_file.name == "customer-support-agent.json"
    assert output_file.parent.name == "business"


def test_business_writer_rejects_non_business_layer(monkeypatch, tmp_path):
    evidence_directory = tmp_path / "evidence"
    model_repository_directory = tmp_path / "model-repo"

    (evidence_directory / "business").mkdir(parents=True)
    (model_repository_directory / ".git").mkdir(parents=True)
    (model_repository_directory / "systems").mkdir()

    monkeypatch.setenv("EVIDENCE_DIR", str(evidence_directory))
    monkeypatch.setenv("MODEL_REPO_DIR", str(model_repository_directory))

    invalid_element = valid_business_element().model_copy(
        update={"layer": "strategy"}
    )

    try:
        persist_business_element(invalid_element)
    except ValueError as error:
        assert "business" in str(error)
    else:
        raise AssertionError("Expected a non-Business element to be rejected.")
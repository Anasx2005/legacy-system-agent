import pytest
from pydantic import ValidationError

from agents.schema import ModelElement


def valid_element_data() -> dict:
    return {
        "id": "customer-portal",
        "layer": "application",
        "archimate_type": "Application Component",
        "name": "Customer Portal",
        "documentation": "A web application used by customers.",
        "confidence": "observed",
        "evidence": [
            {
                "source_type": "source_code",
                "locator": "frontend/src/App.tsx",
            }
        ],
        "relationships": [
            {
                "target_id": "customer-data",
                "type": "Access",
            }
        ],
    }


def test_valid_model_element_is_accepted():
    element = ModelElement.model_validate(valid_element_data())

    assert element.id == "customer-portal"
    assert element.archimate_type == "Application Component"
    assert element.evidence[0].locator == "frontend/src/App.tsx"


def test_empty_evidence_fails_validation():
    data = valid_element_data()
    data["evidence"] = []

    with pytest.raises(ValidationError, match="at least 1 item"):
        ModelElement.model_validate(data)


def test_unknown_archimate_type_fails_validation():
    data = valid_element_data()
    data["archimate_type"] = "Quantum Mainframe"

    with pytest.raises(ValidationError, match="Unknown ArchiMate type"):
        ModelElement.model_validate(data)


def test_archimate_type_in_wrong_layer_fails_validation():
    data = valid_element_data()
    data["layer"] = "business"
    data["archimate_type"] = "Application Component"

    with pytest.raises(ValidationError, match="not valid in layer"):
        ModelElement.model_validate(data)


def test_unknown_relationship_type_fails_validation():
    data = valid_element_data()
    data["relationships"][0]["type"] = "DependsOn"

    with pytest.raises(ValidationError, match="Unknown ArchiMate relationship type"):
        ModelElement.model_validate(data)


def test_blank_documentation_fails_validation():
    data = valid_element_data()
    data["documentation"] = "   "

    with pytest.raises(ValidationError):
        ModelElement.model_validate(data)



"""
Step 05 — use it in every future ingestion agent
Whenever an LLM returns JSON, validate it immediately:
from agents.schema import ModelElement

llm_json = {
    "id": "customer-portal",
    "layer": "application",
    "archimate_type": "Application Component",
    "name": "Customer Portal",
    "documentation": "A web application used by customers.",
    "confidence": "observed",
    "evidence": [
        {
            "source_type": "source_code",
            "locator": "frontend/src/App.tsx",
        }
    ],
    "relationships": [],
}

element = ModelElement.model_validate(llm_json)

"""        
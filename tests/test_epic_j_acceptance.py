"""Epic J fixture and deterministic end-to-end acceptance coverage.

External systems (LLM provider, GitHub and LangSmith) are represented by their
existing integration boundaries here.  The developer runbook describes the
one manual run that exercises those real services.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from agents.reconciler import run_reconciler
from agents.validator import run_validator
from backend.database.base import Base
from backend.database.models.legacy_system import LegacySystem
from backend.services.ingestion import PipelineValidationError, run_as_is_ingestion


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_EVIDENCE = PROJECT_ROOT / "test-fixtures" / "evidence"


def _element(
    element_id: str,
    layer: str,
    archimate_type: str,
    name: str,
    locator: str,
    relationships: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "id": element_id,
        "layer": layer,
        "archimate_type": archimate_type,
        "name": name,
        "documentation": f"Acceptance fixture: {name}",
        "confidence": "observed",
        "evidence": [{"source_type": "fixture", "locator": locator}],
        "relationships": relationships or [],
    }


def _write_element(base_dir: Path, element: dict[str, object]) -> None:
    destination = base_dir / str(element["layer"]) / f"{element['id']}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(element, indent=2) + "\n", encoding="utf-8")


def _seed_all_five_agent_outputs(base_dir: Path, *, invalid_reference: bool) -> None:
    """Deterministic stand-in for E1-E5 output, preserving their source scope."""
    _write_element(base_dir, _element("mot-self-service", "motivation", "Goal", "Customer Self Service", "motivation/customer-experience.md#Goal"))
    _write_element(base_dir, _element("str-self-service", "strategy", "Capability", "Customer Self-Service", "strategy/modernisation-plan.md#Direction"))
    _write_element(base_dir, _element("biz-account-enquiry", "business", "Business Process", "Account Enquiry", "business/customer-support-interview.md#Customer support interview"))
    _write_element(base_dir, _element("app-customer-api", "application", "Application Component", "Customer API", "code/customer_api.py#L4-L10"))
    _write_element(base_dir, _element("app-customer-api-legacy", "application", "Application Component", "customer-api", "code/customer_api.py#L7-L7"))
    _write_element(base_dir, _element("tech-customer-api-host", "technology", "Node", "Customer API Host", "infra/main.tf#L1-L5"))

    relationships: list[dict[str, object]] = [{
        "target_id": "biz-account-enquiry",
        "type": "Serving",
        "evidence": [{"source_type": "fixture", "locator": "integration/customer-api.yaml#L6-L11"}],
    }]
    if invalid_reference:
        relationships.append({
            "target_id": "app-retired-billing-service",
            "type": "Serving",
            "evidence": [{"source_type": "fixture", "locator": "integration/customer-api-invalid.yaml#L5-L9"}],
        })
    app_path = base_dir / "application" / "app-customer-api.json"
    app = json.loads(app_path.read_text(encoding="utf-8"))
    app["relationships"] = relationships
    app_path.write_text(json.dumps(app, indent=2) + "\n", encoding="utf-8")


@pytest.fixture
def acceptance_db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'acceptance.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    with factory() as db:
        system = LegacySystem(name="legacy-system", description="Epic J fixture")
        db.add(system)
        db.commit()
        db.refresh(system)
        system_id = system.id
    try:
        yield factory, system_id
    finally:
        engine.dispose()


def _configure(monkeypatch, tmp_path) -> Path:
    model_base = tmp_path / "model-repo" / "systems" / "legacy-system" / "as-is"
    model_base.mkdir(parents=True)
    monkeypatch.setenv("EVIDENCE_DIR", str(FIXTURE_EVIDENCE))
    monkeypatch.setenv("MODEL_REPO_DIR", str(model_base.parents[2]))
    monkeypatch.setenv("MODEL_SYSTEM_ID", "legacy-system")
    return model_base


def test_j1_fixture_covers_all_source_types_and_edge_cases():
    expected_files = {
        "motivation/customer-experience.md",
        "strategy/modernisation-plan.md",
        "business/customer-support-interview.md",
        "code/customer_api.py",
        "code/customer_schema.sql",
        "infra/main.tf",
        "integration/customer-api.yaml",
        "integration/customer-api-invalid.yaml",
    }
    assert {path.relative_to(FIXTURE_EVIDENCE).as_posix() for path in FIXTURE_EVIDENCE.rglob("*") if path.is_file()} == expected_files
    readme = (PROJECT_ROOT / "test-fixtures" / "README.md").read_text(encoding="utf-8")
    assert "F1 duplicate" in readme
    assert "F2/E5 invalid reference" in readme


def test_j2_invalid_reference_halts_before_git_and_duplicate_is_merged(
    monkeypatch, tmp_path, acceptance_db
):
    factory, system_id = acceptance_db
    model_base = _configure(monkeypatch, tmp_path)
    _seed_all_five_agent_outputs(model_base, invalid_reference=True)

    monkeypatch.setattr("backend.services.ingestion._run_parallel_analysts", lambda run_id: None)
    monkeypatch.setattr("backend.services.ingestion._invoke_subagent", lambda name, run_id: None)
    monkeypatch.setattr("backend.services.ingestion.commit_to_model", lambda *args: pytest.fail("Git must not run after F2 fails"))

    with factory() as db, pytest.raises(PipelineValidationError):
        run_as_is_ingestion("legacy-system", FIXTURE_EVIDENCE, run_id="j-invalid", db=db, system_db_id=system_id)

    reconciliation = json.loads((model_base / "reconciliation-report.json").read_text(encoding="utf-8"))
    assert reconciliation["total_elements_before"] == 6
    assert reconciliation["total_elements_after"] == 5
    assert reconciliation["merges"]
    merged = json.loads((model_base / "application" / "app-customer-api.json").read_text(encoding="utf-8"))
    assert {citation["locator"] for citation in merged["evidence"]} == {"code/customer_api.py#L4-L10", "code/customer_api.py#L7-L7"}
    validation = json.loads((model_base / "validation-report.json").read_text(encoding="utf-8"))
    assert validation["overall_status"] == "FAIL"
    assert any(issue["field"] == "relationships.target_id" for issue in validation["violations"])


def test_j2_clean_run_reaches_commit_and_pull_request(monkeypatch, tmp_path, acceptance_db):
    factory, system_id = acceptance_db
    model_base = _configure(monkeypatch, tmp_path)
    _seed_all_five_agent_outputs(model_base, invalid_reference=False)
    events: list[str] = []

    monkeypatch.setattr("backend.services.ingestion._run_parallel_analysts", lambda run_id: events.append("E1-E4"))
    monkeypatch.setattr("backend.services.ingestion._invoke_subagent", lambda name, run_id: events.append(name))
    monkeypatch.setattr("backend.services.ingestion.commit_to_model", lambda system, run: events.append("G1") or SimpleNamespace(commit_sha="fixture-sha"))
    monkeypatch.setattr("backend.services.ingestion.open_pull_request", lambda **kwargs: events.append("G2") or {"pr_number": 42, "pr_url": "https://github.example/pull/42"})

    with factory() as db:
        result = run_as_is_ingestion("legacy-system", FIXTURE_EVIDENCE, run_id="j-clean", db=db, system_db_id=system_id)

    assert result.pr_number == 42
    assert events == ["E1-E4", "integration-mapper", "G1", "G2"]
    report = run_validator(base_dir=model_base)
    assert report.overall_status == "PASS"
    assert run_reconciler(base_dir=model_base).total_elements_after == 5

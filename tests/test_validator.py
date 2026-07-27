"""
Tests for agents/validator.py (Epic F2).

load_archimate_types_by_layer() and load_relationship_types() normally parse
the archimate-metamodel SKILL.md from disk. To keep these tests fast and
independent of that file, we monkeypatch both functions with a small,
controlled vocabulary that is representative enough to exercise every rule
in agents/validator.py.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agents.validator import (
    ValidationReport,
    Violation,
    ViolationSeverity,
    is_cross_layer_valid,
    run_validator,
)

# ---------------------------------------------------------------------------
# Controlled test vocabulary (stands in for a real SKILL.md)
# ---------------------------------------------------------------------------

FAKE_TYPES_BY_LAYER = {
    "motivation": {"Goal", "Requirement"},
    "strategy": {"Resource", "Capability"},
    "business": {"Business Process", "Business Actor"},
    "application": {"Application Component", "Application Service"},
    "technology": {"Node", "Technology Service"},
}

FAKE_RELATIONSHIP_TYPES = {
    "Serving",
    "Realization",
    "Assignment",
    "Triggering",
    "Flow",
    "Association",
    "Specialization",
    "Composition",
    "Aggregation",
    "Influence",
}


@pytest.fixture(autouse=True)
def patch_metamodel(monkeypatch):
    monkeypatch.setattr(
        "agents.validator.load_archimate_types_by_layer",
        lambda: FAKE_TYPES_BY_LAYER,
    )
    monkeypatch.setattr(
        "agents.validator.load_relationship_types",
        lambda: FAKE_RELATIONSHIP_TYPES,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_element(
    element_id: str,
    layer: str,
    archimate_type: str,
    name: str,
    documentation: str = "test doc",
    confidence: str = "observed",
    evidence: list[dict] | None = None,
    relationships: list[dict] | None = None,
) -> dict:
    return {
        "id": element_id,
        "layer": layer,
        "archimate_type": archimate_type,
        "name": name,
        "documentation": documentation,
        "confidence": confidence,
        "evidence": evidence
        if evidence is not None
        else [{"source_type": "doc", "locator": f"{element_id}-source"}],
        "relationships": relationships or [],
    }


def write_element(base_dir: Path, element: dict) -> Path:
    layer_dir = base_dir / element["layer"]
    layer_dir.mkdir(parents=True, exist_ok=True)
    file_path = layer_dir / f"{element['id']}.json"
    file_path.write_text(json.dumps(element, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return file_path


def write_raw(base_dir: Path, layer: str, element_id: str, raw: dict) -> Path:
    """Write a JSON file that bypasses the make_element() convenience defaults,
    used for deliberately-broken payloads."""
    layer_dir = base_dir / layer
    layer_dir.mkdir(parents=True, exist_ok=True)
    file_path = layer_dir / f"{element_id}.json"
    file_path.write_text(json.dumps(raw, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return file_path


def rel(target_id: str, rel_type: str, locator: str = "rel-source") -> dict:
    return {
        "target_id": target_id,
        "type": rel_type,
        "evidence": [{"source_type": "doc", "locator": locator}],
    }


# ---------------------------------------------------------------------------
# 1. Happy path
# ---------------------------------------------------------------------------

def test_valid_model_passes(tmp_path):
    write_element(
        tmp_path,
        make_element(
            "app-checkout",
            "application",
            "Application Component",
            "Checkout Service",
            relationships=[rel("biz-order", "Serving")],
        ),
    )
    write_element(
        tmp_path,
        make_element("biz-order", "business", "Business Process", "Order Process"),
    )

    report = run_validator(base_dir=tmp_path)

    assert report.overall_status == "PASS"
    assert report.error_count == 0


# ---------------------------------------------------------------------------
# 2. Invalid archimate_type for the layer
# ---------------------------------------------------------------------------

def test_invalid_archimate_type_is_flagged(tmp_path):
    write_element(
        tmp_path,
        make_element("app-checkout", "application", "Not A Real Type", "Checkout Service"),
    )

    report = run_validator(base_dir=tmp_path)

    assert report.overall_status == "FAIL"
    assert report.error_count >= 1
    # In this codebase, ModelElement itself rejects an unknown archimate_type
    # at parse time (validated against the real SKILL.md), so it surfaces as
    # a "schema" parse violation rather than reaching the explicit
    # archimate_type check in run_validator - either way the pipeline must fail.
    assert any(v.element_id == "app-checkout" for v in report.violations)


# ---------------------------------------------------------------------------
# 3. Dangling relationship target
# ---------------------------------------------------------------------------

def test_dangling_relationship_target_is_flagged(tmp_path):
    write_element(
        tmp_path,
        make_element(
            "app-checkout",
            "application",
            "Application Component",
            "Checkout Service",
            relationships=[rel("does-not-exist", "Serving")],
        ),
    )

    report = run_validator(base_dir=tmp_path)

    assert report.overall_status == "FAIL"
    assert any(v.field == "relationships.target_id" for v in report.violations)


# ---------------------------------------------------------------------------
# 4. Illegal cross-layer relationship (Composition across layers)
# ---------------------------------------------------------------------------

def test_cross_layer_composition_is_invalid(tmp_path):
    write_element(
        tmp_path,
        make_element(
            "app-checkout",
            "application",
            "Application Component",
            "Checkout Service",
            relationships=[rel("biz-order", "Composition")],
        ),
    )
    write_element(
        tmp_path,
        make_element("biz-order", "business", "Business Process", "Order Process"),
    )

    report = run_validator(base_dir=tmp_path)

    assert report.overall_status == "FAIL"
    assert any(
        v.field == "relationships" and "Composition" in v.message for v in report.violations
    )


def test_is_cross_layer_valid_directly():
    ok, _ = is_cross_layer_valid("technology", "application", "Serving", "Node", "Application Component")
    assert ok is True

    bad, _ = is_cross_layer_valid(
        "business", "application", "Composition", "Business Process", "Application Component"
    )
    assert bad is False

    universal, _ = is_cross_layer_valid(
        "business", "technology", "Association", "Business Process", "Node"
    )
    assert universal is True


# ---------------------------------------------------------------------------
# 5. Empty layer -> warning, not error
# ---------------------------------------------------------------------------

def test_empty_layer_produces_warning_not_error(tmp_path):
    write_element(
        tmp_path,
        make_element("app-checkout", "application", "Application Component", "Checkout Service"),
    )

    report = run_validator(base_dir=tmp_path)

    # Model is otherwise valid, so overall_status should still be PASS.
    assert report.overall_status == "PASS"
    warning_layers = {v.details or v.message for v in report.warnings}
    assert any("business" in w for w in warning_layers) or any(
        "business" in w.message for w in report.warnings
    )


# ---------------------------------------------------------------------------
# 6. Missing evidence (defense in depth, raw JSON bypassing convenience helper)
# ---------------------------------------------------------------------------

def test_missing_evidence_is_flagged(tmp_path):
    raw = {
        "id": "app-checkout",
        "layer": "application",
        "archimate_type": "Application Component",
        "name": "Checkout Service",
        "documentation": "test doc",
        "confidence": "observed",
        "evidence": [],
        "relationships": [],
    }
    write_raw(tmp_path, "application", "app-checkout", raw)

    report = run_validator(base_dir=tmp_path)

    assert report.overall_status == "FAIL"
    # Depending on whether ModelElement enforces min_length=1 on evidence at
    # the Pydantic layer, this surfaces either as an explicit "evidence"
    # violation or as a schema-parse violation - either way it must fail.
    assert report.error_count >= 1


# ---------------------------------------------------------------------------
# 7. Report file is written and parseable
# ---------------------------------------------------------------------------

def test_report_file_is_written_and_parseable(tmp_path):
    write_element(
        tmp_path,
        make_element("app-checkout", "application", "Application Component", "Checkout Service"),
    )

    run_validator(base_dir=tmp_path)

    report_path = tmp_path / "validation-report.json"
    assert report_path.exists()
    data = json.loads(report_path.read_text(encoding="utf-8"))
    parsed = ValidationReport.model_validate(data)
    assert parsed.total_elements == 1


# ---------------------------------------------------------------------------
# 8. Invalid relationship type
# ---------------------------------------------------------------------------

def test_invalid_relationship_type_is_flagged(tmp_path):
    write_element(
        tmp_path,
        make_element(
            "app-checkout",
            "application",
            "Application Component",
            "Checkout Service",
            relationships=[rel("biz-order", "TotallyMadeUpRelationship")],
        ),
    )
    write_element(
        tmp_path,
        make_element("biz-order", "business", "Business Process", "Order Process"),
    )

    report = run_validator(base_dir=tmp_path)

    assert report.overall_status == "FAIL"
    assert report.error_count >= 1
    # Same reason as test_invalid_archimate_type_is_flagged above: Relationship
    # itself rejects an unrecognized type at parse time, so app-checkout fails
    # to load entirely and shows up as a "schema" violation, not
    # "relationships.type". The pipeline still correctly fails either way.
    assert any(v.element_id == "app-checkout" for v in report.violations)
    
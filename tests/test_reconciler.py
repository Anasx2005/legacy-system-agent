"""
Tests for agents/reconciler.py (Epic F1).

All tests use pytest's tmp_path fixture to build a throwaway
systems/<system>/as-is/ style directory tree, so no env vars or a real
model repo are needed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agents.reconciler import (
    ConflictRecord,
    MergeRecord,
    ReconciliationReport,
    find_near_misses,
    load_all_elements,
    merge_elements,
    normalize_name,
    repoint_relationships,
    run_reconciler,
)
from agents.schema import ModelElement


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


def rel(target_id: str, rel_type: str, locator: str = "rel-source") -> dict:
    return {
        "target_id": target_id,
        "type": rel_type,
        "evidence": [{"source_type": "doc", "locator": locator}],
    }


# ---------------------------------------------------------------------------
# 1. Core merge logic
# ---------------------------------------------------------------------------

def test_exact_duplicates_are_merged_and_keep_all_evidence(tmp_path):
    write_element(
        tmp_path,
        make_element(
            "app-payment-service",
            "application",
            "Application Component",
            "Payment Service",
            evidence=[{"source_type": "code", "locator": "src/payment.py:10"}],
        ),
    )
    write_element(
        tmp_path,
        make_element(
            "app-paymentsvc",
            "application",
            "Application Component",
            "payment-service",
            evidence=[{"source_type": "doc", "locator": "docs/architecture.md#payments"}],
        ),
    )

    report = run_reconciler(base_dir=tmp_path)

    assert report.total_elements_before == 2
    assert report.total_elements_after == 1
    assert len(report.merges) == 1

    reconciled = load_all_elements(tmp_path)
    assert len(reconciled) == 1
    merged = reconciled[0]
    locators = {e.locator for e in merged.evidence}
    assert locators == {"src/payment.py:10", "docs/architecture.md#payments"}


# ---------------------------------------------------------------------------
# 2. Near-miss detection
# ---------------------------------------------------------------------------

def test_near_miss_is_flagged_not_merged(tmp_path):
    write_element(
        tmp_path,
        make_element("app-payment-service", "application", "Application Component", "Payment Service"),
    )
    write_element(
        tmp_path,
        make_element("app-paymentsvc-2", "application", "Application Component", "PaymentSvc"),
    )

    report = run_reconciler(base_dir=tmp_path)

    assert report.total_elements_after == 2  # NOT merged
    assert len(report.merges) == 0
    assert len(report.conflicts) == 1
    conflict = report.conflicts[0]
    assert isinstance(conflict, ConflictRecord)
    assert "near-miss" in conflict.reason


# ---------------------------------------------------------------------------
# 3. Type-scoping: same name, different type -> never merged
# ---------------------------------------------------------------------------

def test_same_name_different_type_not_merged(tmp_path):
    write_element(
        tmp_path,
        make_element("biz-payment-service", "business", "Business Process", "Payment Service"),
    )
    write_element(
        tmp_path,
        make_element("app-payment-service", "application", "Application Component", "Payment Service"),
    )

    report = run_reconciler(base_dir=tmp_path)

    assert report.total_elements_after == 2
    assert len(report.merges) == 0


# ---------------------------------------------------------------------------
# 4. Re-pointing relationships to the canonical id
# ---------------------------------------------------------------------------

def test_relationship_repointed_to_canonical_id(tmp_path):
    write_element(
        tmp_path,
        make_element("app-payment-service", "application", "Application Component", "Payment Service"),
    )
    write_element(
        tmp_path,
        make_element("app-paymentsvc", "application", "Application Component", "payment-service"),
    )
    # A third element has a relationship pointing at the element that will be merged away.
    write_element(
        tmp_path,
        make_element(
            "app-checkout",
            "application",
            "Application Component",
            "Checkout Service",
            relationships=[rel("app-paymentsvc", "Serving")],
        ),
    )

    run_reconciler(base_dir=tmp_path)

    reconciled = {e.id: e for e in load_all_elements(tmp_path)}
    assert "app-paymentsvc" not in reconciled  # merged away
    checkout = reconciled["app-checkout"]
    targets = {r.target_id for r in checkout.relationships}
    assert "app-payment-service" in targets  # canonical id (alphabetically first)
    assert "app-paymentsvc" not in targets


# ---------------------------------------------------------------------------
# 5. Determinism
# ---------------------------------------------------------------------------

def test_reconciler_is_deterministic(tmp_path):
    def build(dir_path: Path):
        write_element(
            dir_path,
            make_element("app-payment-service", "application", "Application Component", "Payment Service"),
        )
        write_element(
            dir_path,
            make_element("app-paymentsvc", "application", "Application Component", "payment-service"),
        )

    dir_a = tmp_path / "run_a"
    dir_b = tmp_path / "run_b"
    dir_a.mkdir()
    dir_b.mkdir()
    build(dir_a)
    build(dir_b)

    run_reconciler(base_dir=dir_a)
    run_reconciler(base_dir=dir_b)

    elements_a = sorted(load_all_elements(dir_a), key=lambda e: e.id)
    elements_b = sorted(load_all_elements(dir_b), key=lambda e: e.id)

    assert len(elements_a) == len(elements_b) == 1
    assert elements_a[0].model_dump(mode="json") == elements_b[0].model_dump(mode="json")


# ---------------------------------------------------------------------------
# 6. Passthrough: no duplicates -> nothing changes
# ---------------------------------------------------------------------------

def test_single_element_passes_through_unchanged(tmp_path):
    write_element(
        tmp_path,
        make_element("app-checkout", "application", "Application Component", "Checkout Service"),
    )

    report = run_reconciler(base_dir=tmp_path)

    assert report.total_elements_before == 1
    assert report.total_elements_after == 1
    assert len(report.merges) == 0
    assert len(report.conflicts) == 0


# ---------------------------------------------------------------------------
# 7. Report file is written and parseable
# ---------------------------------------------------------------------------

def test_report_file_is_written_and_parseable(tmp_path):
    write_element(
        tmp_path,
        make_element("app-checkout", "application", "Application Component", "Checkout Service"),
    )

    run_reconciler(base_dir=tmp_path)

    report_path = tmp_path / "reconciliation-report.json"
    assert report_path.exists()
    data = json.loads(report_path.read_text(encoding="utf-8"))
    parsed = ReconciliationReport.model_validate(data)
    assert parsed.total_elements_after == 1


# ---------------------------------------------------------------------------
# Unit-level tests for the small helper functions
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Payment Service", "paymentservice"),
        ("payment-service", "paymentservice"),
        ("  Payment   Service  ", "paymentservice"),
        ("Order_Processing!", "orderprocessing"),
    ],
)
def test_normalize_name(raw, expected):
    assert normalize_name(raw) == expected


def test_merge_elements_prefers_observed_confidence():
    a = ModelElement.model_validate(
        make_element(
            "app-a",
            "application",
            "Application Component",
            "Svc",
            confidence="inferred",
        )
    )
    b = ModelElement.model_validate(
        make_element(
            "app-b",
            "application",
            "Application Component",
            "Svc",
            confidence="observed",
        )
    )
    merged, merged_away = merge_elements([a, b])
    assert merged.confidence == "observed"
    assert merged_away == ["app-b"]


def test_find_near_misses_ignores_exact_matches():
    a = ModelElement.model_validate(
        make_element("app-a", "application", "Application Component", "Payment Service")
    )
    b = ModelElement.model_validate(
        make_element("app-b", "application", "Application Component", "Payment Service")
    )
    # Exact normalized match should not show up as a near-miss (it would be merged upstream instead).
    assert find_near_misses([a, b]) == []


def test_repoint_relationships_noop_when_no_merges():
    a = ModelElement.model_validate(
        make_element(
            "app-a",
            "application",
            "Application Component",
            "Svc",
            relationships=[rel("app-b", "Serving")],
        )
    )
    result = repoint_relationships([a], id_map={})
    assert result[0].relationships[0].target_id == "app-b"
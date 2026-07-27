"""
Epic F — F2: Validator

Deterministic (no LLM) validation of the reconciled model output against the
ArchiMate metamodel rules from the archimate-metamodel skill. This is the
last gate before the pipeline is allowed to commit to git (Epic G / Epic H).

Checks performed, in order:
  1. Schema validity        - can every JSON file parse into a ModelElement?
  2. Type-layer match       - is archimate_type valid for this layer?
  3. Relationship type      - is the relationship type recognized at all?
  4. Relationship target    - does target_id reference a real element?
  5. Cross-layer validity   - is this relationship type allowed between
                               these two layers (per SKILL.md section 3.2)?
  6. Evidence completeness  - does every element have >= 1 evidence citation?
  7. Coverage               - how many elements/relationships per layer
                               (empty layer -> warning, not error).

overall_status is "FAIL" if any error-severity violation exists, "PASS"
otherwise. Epic H must check this and refuse to proceed to git commit on FAIL.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from agents.reconciler import _model_base_dir
from agents.schema import (
    LAYER_NAMES,
    ModelElement,
    load_archimate_types_by_layer,
    load_relationship_types,
)


# ---------------------------------------------------------------------------
# Report data structures
# ---------------------------------------------------------------------------

class ViolationSeverity(str, Enum):
    error = "error"
    warning = "warning"


class Violation(BaseModel):
    severity: ViolationSeverity
    element_id: str
    field: str
    message: str
    details: Optional[str] = None


class LayerCoverage(BaseModel):
    layer: str
    element_count: int
    relationship_count: int
    element_types: list[str]


class ValidationReport(BaseModel):
    overall_status: str  # "PASS" or "FAIL"
    total_elements: int
    total_relationships: int
    violations: list[Violation]
    warnings: list[Violation]
    coverage: list[LayerCoverage]
    error_count: int
    warning_count: int


# ---------------------------------------------------------------------------
# Cross-layer relationship rules (SKILL.md section 3.2)
# ---------------------------------------------------------------------------

# Relationships that are only ever valid within a single layer.
INTRA_LAYER_ONLY = {"Composition", "Aggregation"}

# Cross-layer: (source_layer, target_layer) -> allowed relationship types.
CROSS_LAYER_RULES: dict[tuple[str, str], set[str]] = {
    ("technology", "application"): {"Serving", "Realization"},
    ("application", "technology"): {"Assignment"},
    ("application", "business"): {"Serving", "Realization"},
    ("business", "application"): {"Triggering", "Flow"},
    ("business", "motivation"): {"Realization", "Influence"},
    ("strategy", "motivation"): {"Realization", "Influence"},
    ("business", "strategy"): {"Realization"},
}

# Valid between any two elements regardless of layer.
UNIVERSAL = {"Association"}


def is_cross_layer_valid(
    source_layer: str,
    target_layer: str,
    rel_type: str,
    source_type: str,
    target_type: str,
) -> tuple[bool, str]:
    if rel_type in UNIVERSAL:
        return True, "Association is universally valid"

    if rel_type == "Specialization":
        if source_type == target_type:
            return True, "Specialization between same types"
        return False, f"Specialization requires same type, got {source_type} -> {target_type}"

    if source_layer == target_layer:
        return True, f"Intra-layer {rel_type} within {source_layer}"

    if rel_type in INTRA_LAYER_ONLY:
        return False, f"{rel_type} is not valid across layers ({source_layer} -> {target_layer})"

    pair = (source_layer, target_layer)
    if pair in CROSS_LAYER_RULES:
        if rel_type in CROSS_LAYER_RULES[pair]:
            return True, f"Valid: {rel_type} from {source_layer} to {target_layer}"
        return False, f"{rel_type} not allowed from {source_layer} to {target_layer}"

    return False, f"No cross-layer rule for {source_layer} -> {target_layer} with {rel_type}"


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_and_validate_elements(
    base_dir: Path,
) -> tuple[list[ModelElement], list[Violation]]:
    """Load elements, collecting parse/schema errors as violations."""
    elements: list[ModelElement] = []
    parse_errors: list[Violation] = []

    for layer in LAYER_NAMES:
        layer_dir = base_dir / layer
        if not layer_dir.exists():
            continue
        for fp in sorted(layer_dir.glob("*.json")):
            try:
                data = json.loads(fp.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                parse_errors.append(
                    Violation(
                        severity=ViolationSeverity.error,
                        element_id=fp.stem,
                        field="file",
                        message=f"Invalid JSON: {e}",
                    )
                )
                continue
            try:
                elements.append(ModelElement.model_validate(data))
            except Exception as e:  # noqa: BLE001 - defense in depth, reported as violation
                parse_errors.append(
                    Violation(
                        severity=ViolationSeverity.error,
                        element_id=fp.stem,
                        field="schema",
                        message=f"Schema validation failed: {e}",
                    )
                )

    return elements, parse_errors


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------

def run_validator(base_dir: Path | None = None) -> ValidationReport:
    if base_dir is None:
        base_dir = _model_base_dir()

    violations: list[Violation] = []
    warnings: list[Violation] = []

    # Load & parse
    elements, parse_errors = load_and_validate_elements(base_dir)
    violations.extend(parse_errors)

    element_ids = {e.id for e in elements}
    element_map = {e.id: e for e in elements}
    types_by_layer = load_archimate_types_by_layer()
    valid_rel_types = load_relationship_types()

    for element in elements:
        # 2. Type-layer match (Pydantic may already reject this; defense in depth)
        if element.archimate_type not in types_by_layer.get(element.layer, set()):
            violations.append(
                Violation(
                    severity=ViolationSeverity.error,
                    element_id=element.id,
                    field="archimate_type",
                    message=(
                        f"'{element.archimate_type}' not valid for layer "
                        f"'{element.layer}'"
                    ),
                )
            )

        # 6. Evidence completeness
        if len(element.evidence) == 0:
            violations.append(
                Violation(
                    severity=ViolationSeverity.error,
                    element_id=element.id,
                    field="evidence",
                    message="No evidence citations",
                )
            )

        # 3-5. Relationships
        for rel in element.relationships:
            if rel.type not in valid_rel_types:
                violations.append(
                    Violation(
                        severity=ViolationSeverity.error,
                        element_id=element.id,
                        field="relationships.type",
                        message=f"Invalid relationship type: '{rel.type}'",
                    )
                )

            if rel.target_id not in element_ids:
                violations.append(
                    Violation(
                        severity=ViolationSeverity.error,
                        element_id=element.id,
                        field="relationships.target_id",
                        message=f"Target '{rel.target_id}' does not exist",
                    )
                )
            elif rel.type in valid_rel_types:
                target = element_map[rel.target_id]
                valid, reason = is_cross_layer_valid(
                    element.layer,
                    target.layer,
                    rel.type,
                    element.archimate_type,
                    target.archimate_type,
                )
                if not valid:
                    violations.append(
                        Violation(
                            severity=ViolationSeverity.error,
                            element_id=element.id,
                            field="relationships",
                            message=f"Invalid: {element.id} --[{rel.type}]--> {rel.target_id}",
                            details=reason,
                        )
                    )

    # 7. Coverage analysis
    coverage: list[LayerCoverage] = []
    total_rels = 0
    layer_elems: dict[str, list[ModelElement]] = defaultdict(list)
    for e in elements:
        layer_elems[e.layer].append(e)

    for layer in LAYER_NAMES:
        elems = layer_elems.get(layer, [])
        rc = sum(len(e.relationships) for e in elems)
        total_rels += rc
        coverage.append(
            LayerCoverage(
                layer=layer,
                element_count=len(elems),
                relationship_count=rc,
                element_types=sorted({e.archimate_type for e in elems}),
            )
        )
        if not elems:
            warnings.append(
                Violation(
                    severity=ViolationSeverity.warning,
                    element_id="N/A",
                    field="coverage",
                    message=f"Layer '{layer}' has no elements",
                )
            )

    error_count = sum(1 for v in violations if v.severity == ViolationSeverity.error)

    report = ValidationReport(
        overall_status="FAIL" if error_count > 0 else "PASS",
        total_elements=len(elements),
        total_relationships=total_rels,
        violations=violations,
        warnings=warnings,
        coverage=coverage,
        error_count=error_count,
        warning_count=len(warnings),
    )

    report_path = base_dir / "validation-report.json"
    report_path.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )

    status = "PASS" if report.overall_status == "PASS" else "FAIL"
    print(f"[validator] {status}")
    print(f"[validator] Elements: {report.total_elements}, Rels: {report.total_relationships}")
    print(f"[validator] Errors: {error_count}, Warnings: {len(warnings)}")

    return report


if __name__ == "__main__":
    result = run_validator()
    # Non-zero exit code lets Epic H's orchestration halt the pipeline on FAIL.
    sys.exit(0 if result.overall_status == "PASS" else 1)
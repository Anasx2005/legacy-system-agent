"""
Epic F — F1: Reconciler

Deterministic (no LLM) merging of near-duplicate ArchiMate elements produced
by the five Epic E ingestion subagents.

Two elements are considered duplicates for MVP purposes if and only if:
  1. They share the same archimate_type, AND
  2. Their names are identical after normalization (lowercase, strip
     punctuation, strip whitespace).

Anything that looks similar but does not match exactly after normalization
is flagged as a "conflict" for human review — never silently merged, never
silently dropped.

This module has zero LLM calls. Given the same input files, it always
produces the same output (Reproducibility quality attribute).
"""

from __future__ import annotations

import json
import os
import re
import string
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

from pydantic import BaseModel

from agents.schema import EvidenceCitation, LAYER_NAMES, ModelElement, Relationship

NEAR_MISS_THRESHOLD = 0.8


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def normalize_name(name: str) -> str:
    """Lowercase -> strip punctuation -> strip all whitespace."""
    name = name.lower()
    name = name.translate(str.maketrans("", "", string.punctuation))
    name = re.sub(r"\s+", "", name)
    return name


# ---------------------------------------------------------------------------
# Report data structures
# ---------------------------------------------------------------------------

class MergeRecord(BaseModel):
    canonical_id: str
    merged_id: str
    canonical_name: str
    merged_name: str
    archimate_type: str
    layer: str
    reason: str  # "normalized-name-match"


class ConflictRecord(BaseModel):
    element_a_id: str
    element_b_id: str
    element_a_name: str
    element_b_name: str
    archimate_type: str
    similarity_score: float
    reason: str  # "near-miss: similarity 0.85 ..."


class ReconciliationReport(BaseModel):
    total_elements_before: int
    total_elements_after: int
    merges: list[MergeRecord]
    conflicts: list[ConflictRecord]
    elements_unchanged: int


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def _model_base_dir() -> Path:
    """
    Resolve the as-is directory the same way model_element_writer.py does:
    MODEL_REPO_DIR / systems / MODEL_SYSTEM_ID / as-is
    """
    model_repo = os.environ.get("MODEL_REPO_DIR")
    if not model_repo:
        raise RuntimeError("MODEL_REPO_DIR environment variable is not set")
    system_id = os.environ.get("MODEL_SYSTEM_ID", "legacy-system")

    project_root = Path(__file__).resolve().parent.parent
    repo_path = Path(model_repo)
    if not repo_path.is_absolute():
        repo_path = project_root / model_repo

    return repo_path.resolve() / "systems" / system_id / "as-is"


def load_all_elements(base_dir: Path) -> list[ModelElement]:
    """Load every element JSON file under base_dir/<layer>/*.json."""
    elements: list[ModelElement] = []
    for layer in LAYER_NAMES:
        layer_dir = base_dir / layer
        if not layer_dir.exists():
            continue
        for file_path in sorted(layer_dir.glob("*.json")):
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                elements.append(ModelElement.model_validate(data))
            except Exception as e:  # noqa: BLE001 - deliberately broad, logged below
                print(f"[reconciler] WARNING: Skipping {file_path.name}: {e}")
    return elements


# ---------------------------------------------------------------------------
# Merging
# ---------------------------------------------------------------------------

def merge_elements(group: list[ModelElement]) -> tuple[ModelElement, list[str]]:
    """
    Merge a group of duplicate elements into one canonical element.

    Returns (merged_element, list_of_merged_away_ids).
    """
    group = sorted(group, key=lambda e: e.id)  # deterministic: alphabetically first wins
    canonical = group[0]

    all_evidence = list(canonical.evidence)
    all_relationships = list(canonical.relationships)
    all_docs = [canonical.documentation]
    best_confidence = canonical.confidence
    merged_away_ids: list[str] = []

    existing_locators = {e.locator for e in all_evidence}
    existing_rels = {(r.target_id, r.type) for r in all_relationships}

    for other in group[1:]:
        merged_away_ids.append(other.id)

        for ev in other.evidence:
            if ev.locator not in existing_locators:
                all_evidence.append(ev)
                existing_locators.add(ev.locator)

        for rel in other.relationships:
            if (rel.target_id, rel.type) not in existing_rels:
                all_relationships.append(rel)
                existing_rels.add((rel.target_id, rel.type))

        if other.documentation and other.documentation not in all_docs:
            all_docs.append(other.documentation)

        if other.confidence == "observed":
            best_confidence = "observed"

    merged = ModelElement.model_validate(
        {
            "id": canonical.id,
            "layer": canonical.layer,
            "archimate_type": canonical.archimate_type,
            "name": canonical.name,
            "documentation": " | ".join(all_docs),
            "confidence": best_confidence,
            "evidence": [e.model_dump(mode="json") for e in all_evidence],
            "relationships": [r.model_dump(mode="json") for r in all_relationships],
        }
    )

    return merged, merged_away_ids


def repoint_relationships(
    elements: list[ModelElement], id_map: dict[str, str]
) -> list[ModelElement]:
    """Update any relationship whose target_id points at a merged-away id."""
    updated: list[ModelElement] = []
    for element in elements:
        new_rels = []
        changed = False
        for rel in element.relationships:
            new_target = id_map.get(rel.target_id, rel.target_id)
            if new_target != rel.target_id:
                rel_data = rel.model_dump(mode="json")
                rel_data["target_id"] = new_target
                new_rels.append(Relationship.model_validate(rel_data))
                changed = True
            else:
                new_rels.append(rel)

        if changed:
            elem_data = element.model_dump(mode="json")
            elem_data["relationships"] = [r.model_dump(mode="json") for r in new_rels]
            updated.append(ModelElement.model_validate(elem_data))
        else:
            updated.append(element)
    return updated


# ---------------------------------------------------------------------------
# Near-miss detection (flagged, never auto-merged)
# ---------------------------------------------------------------------------

def find_near_misses(elements: list[ModelElement]) -> list[ConflictRecord]:
    """Find pairs of same-type elements whose names are similar but not equal."""
    conflicts: list[ConflictRecord] = []
    by_type: dict[str, list[ModelElement]] = defaultdict(list)
    for e in elements:
        by_type[e.archimate_type].append(e)

    for atype, type_elems in by_type.items():
        type_elems = sorted(type_elems, key=lambda e: e.id)
        for i in range(len(type_elems)):
            for j in range(i + 1, len(type_elems)):
                a, b = type_elems[i], type_elems[j]
                norm_a = normalize_name(a.name)
                norm_b = normalize_name(b.name)
                if norm_a != norm_b:
                    ratio = SequenceMatcher(None, norm_a, norm_b).ratio()
                    if ratio >= NEAR_MISS_THRESHOLD:
                        conflicts.append(
                            ConflictRecord(
                                element_a_id=a.id,
                                element_b_id=b.id,
                                element_a_name=a.name,
                                element_b_name=b.name,
                                archimate_type=atype,
                                similarity_score=round(ratio, 3),
                                reason=(
                                    f"near-miss: similarity {ratio:.3f} "
                                    f"above threshold {NEAR_MISS_THRESHOLD}"
                                ),
                            )
                        )
    return conflicts


# ---------------------------------------------------------------------------
# Serialization (must match model_element_writer.py exactly)
# ---------------------------------------------------------------------------

def _serialize_element(element: ModelElement) -> str:
    return json.dumps(
        element.model_dump(mode="json"),
        indent=2,
        sort_keys=True,
    ) + "\n"


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------

def run_reconciler(base_dir: Path | None = None) -> ReconciliationReport:
    if base_dir is None:
        base_dir = _model_base_dir()

    # 1. Load all elements produced by E1-E5
    all_elements = load_all_elements(base_dir)
    total_before = len(all_elements)

    # 2. Group by (archimate_type, normalized_name)
    groups: dict[tuple[str, str], list[ModelElement]] = defaultdict(list)
    for element in all_elements:
        key = (element.archimate_type, normalize_name(element.name))
        groups[key].append(element)

    # 3. Merge exact-match duplicates
    reconciled: list[ModelElement] = []
    merge_records: list[MergeRecord] = []
    id_map: dict[str, str] = {}

    for (atype, _norm_name), group in sorted(groups.items()):
        if len(group) == 1:
            reconciled.append(group[0])
        else:
            merged, merged_ids = merge_elements(group)
            reconciled.append(merged)
            for mid in merged_ids:
                id_map[mid] = merged.id
                original = next(e for e in group if e.id == mid)
                merge_records.append(
                    MergeRecord(
                        canonical_id=merged.id,
                        merged_id=mid,
                        canonical_name=merged.name,
                        merged_name=original.name,
                        archimate_type=atype,
                        layer=merged.layer,
                        reason="normalized-name-match",
                    )
                )

    # 4. Re-point relationships that referenced merged-away ids
    reconciled = repoint_relationships(reconciled, id_map)

    # 5. Detect near-misses among the reconciled set (flag only, never merge)
    conflicts = find_near_misses(reconciled)

    # 6. Rewrite the as-is directory with the reconciled element set
    for layer in LAYER_NAMES:
        layer_dir = base_dir / layer
        if layer_dir.exists():
            for f in layer_dir.glob("*.json"):
                f.unlink()

    for element in reconciled:
        layer_dir = base_dir / element.layer
        layer_dir.mkdir(parents=True, exist_ok=True)
        file_path = layer_dir / f"{element.id}.json"
        file_path.write_text(_serialize_element(element), encoding="utf-8")

    # 7. Write the reconciliation report
    report = ReconciliationReport(
        total_elements_before=total_before,
        total_elements_after=len(reconciled),
        merges=merge_records,
        conflicts=conflicts,
        elements_unchanged=len(reconciled) - len({r.canonical_id for r in merge_records}),
    )

    report_path = base_dir / "reconciliation-report.json"
    report_path.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"[reconciler] Elements: {total_before} -> {len(reconciled)}")
    print(f"[reconciler] Merges: {len(merge_records)}")
    print(f"[reconciler] Conflicts flagged: {len(conflicts)}")

    return report


if __name__ == "__main__":
    run_reconciler()
"""Validated cross-layer relationship writer for Epic E5."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, ConfigDict, Field

from agents.schema import ModelElement, Relationship


PROJECT_ROOT = Path(__file__).resolve().parent.parent

INTEGRATION_LINE_RANGE = re.compile(
    r"^(?:/evidence/)?integration/.+#L\d+(?:-L\d+)?$"
)


class RelationshipWriteRequest(BaseModel):
    """One relationship update applied to an existing source element."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_id: str = Field(
        min_length=1,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )
    relationship: Relationship


def _configured_directory(environment_variable: str) -> Path:
    configured_value = os.environ.get(environment_variable)

    if not configured_value:
        raise RuntimeError(f"{environment_variable} is required in .env.")

    directory = Path(configured_value)

    if not directory.is_absolute():
        directory = PROJECT_ROOT / directory

    directory = directory.resolve()

    if not directory.is_dir():
        raise RuntimeError(f"Missing directory: {directory}")

    return directory


def _current_model_index(model_repository_directory: Path) -> dict[str, Path]:
    """Return element ID -> JSON file, rejecting duplicate IDs."""
    system_id = os.environ.get("MODEL_SYSTEM_ID", "legacy-system")

    model_root = (
        model_repository_directory
        / "systems"
        / system_id
        / "as-is"
    )

    index: dict[str, Path] = {}

    for json_file in model_root.rglob("*.json"):
        element = ModelElement.model_validate_json(
            json_file.read_text(encoding="utf-8")
        )

        if element.id in index:
            raise ValueError(
                f"Duplicate element ID in current model output: {element.id}"
            )

        index[element.id] = json_file

    return index


def persist_integration_relationship(request: RelationshipWriteRequest) -> Path:
    """Add one evidence-backed relationship to an existing source element."""
    evidence_directory = _configured_directory("EVIDENCE_DIR")
    model_repository_directory = _configured_directory("MODEL_REPO_DIR")

    index = _current_model_index(model_repository_directory)

    if request.source_id not in index:
        raise ValueError(
            f"Source element ID does not exist in current model output: "
            f"{request.source_id}"
        )

    if request.relationship.target_id not in index:
        raise ValueError(
            f"Target element ID does not exist in current model output: "
            f"{request.relationship.target_id}"
        )

    if request.source_id == request.relationship.target_id:
        raise ValueError("A relationship cannot target its own source element.")

    for citation in request.relationship.evidence:
        locator = citation.locator.replace("\\", "/")

        if not INTEGRATION_LINE_RANGE.fullmatch(locator):
            raise ValueError(
                "Integration relationship evidence must use a real file and "
                "line range, for example integration/openapi.yaml#L10-L24. "
                f"Received: {citation.locator}"
            )

        file_part = locator.split("#", maxsplit=1)[0]
        evidence_file = (evidence_directory / file_part).resolve()

        if not evidence_file.is_file():
            raise ValueError(
                f"Integration evidence file does not exist: {citation.locator}"
            )

    source_file = index[request.source_id]
    source_element = ModelElement.model_validate_json(
        source_file.read_text(encoding="utf-8")
    )

    relationship_already_exists = any(
        existing.target_id == request.relationship.target_id
        and existing.type == request.relationship.type
        and existing.evidence == request.relationship.evidence
        for existing in source_element.relationships
    )

    if not relationship_already_exists:
        source_element.relationships.append(request.relationship)

        source_file.write_text(
            json.dumps(
                source_element.model_dump(mode="json"),
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    return source_file


def create_integration_relationship_writer() -> StructuredTool:
    """Return E5's only relationship-persistence tool."""

    def write_integration_relationship(
        source_id: str,
        relationship: dict,
    ) -> str:
        request = RelationshipWriteRequest(
            source_id=source_id,
            relationship=relationship,
        )

        output_file = persist_integration_relationship(request)

        return (
            f"Validated {request.relationship.type} relationship from "
            f"{request.source_id} to {request.relationship.target_id} "
            f"written to {output_file.name}"
        )

    return StructuredTool.from_function(
        func=write_integration_relationship,
        name="write_integration_relationship",
        description=(
            "Add one evidence-backed Serving, Flow, or Realization relationship "
            "between two existing model element IDs."
        ),
        args_schema=RelationshipWriteRequest,
    )
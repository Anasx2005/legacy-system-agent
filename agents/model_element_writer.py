"""Validated writer for ArchiMate model-element JSON files."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from langchain_core.tools import StructuredTool

from agents.schema import ModelElement


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ALLOWED_LAYERS = {"motivation", "strategy"}
ALLOWED_EVIDENCE_FOLDERS = {"motivation", "strategy"}


def _configured_directory(environment_variable: str) -> Path:
    """Load and validate one configured directory."""
    configured_value = os.environ.get(environment_variable)

    if not configured_value:
        raise RuntimeError(f"{environment_variable} is required in .env.")

    directory = Path(configured_value)

    if not directory.is_absolute():
        directory = PROJECT_ROOT / directory

    directory = directory.resolve()

    if not directory.is_dir():
        raise RuntimeError(
            f"{environment_variable} is not an existing directory: {directory}"
        )

    return directory


def _validate_evidence_locator(locator: str, evidence_directory: Path) -> None:
    """
    Confirm that an evidence locator points to a real allowed evidence file.

    Accepted examples:
    - strategy/modernisation-plan.md#Customer self-service
    - motivation/customer-experience.md#Business goal
    """
    file_part = locator.split("#", maxsplit=1)[0].replace("\\", "/")

    if file_part.startswith("/evidence/"):
        file_part = file_part.removeprefix("/evidence/")

    relative_path = Path(file_part)

    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError(f"Unsafe evidence locator: {locator}")

    if not relative_path.parts or relative_path.parts[0] not in ALLOWED_EVIDENCE_FOLDERS:
        raise ValueError(
            "E1 evidence must come from strategy/ or motivation/. "
            f"Received: {locator}"
        )

    evidence_file = (evidence_directory / relative_path).resolve()

    try:
        evidence_file.relative_to(evidence_directory)
    except ValueError:
        raise ValueError(f"Evidence locator escapes the evidence directory: {locator}") from None

    if not evidence_file.is_file():
        raise ValueError(
            "Evidence file does not exist for locator: "
            f"{locator}"
        )


def persist_strategy_element(element: ModelElement) -> Path:
    """
    Validate evidence and save one JSON file into the model Git checkout.

    Existing files with identical content are left unchanged. This makes
    repeated runs stable and avoids needless Git diffs.
    """
    if element.layer not in ALLOWED_LAYERS:
        raise ValueError(
            "strategy-analyst can only write motivation or strategy elements. "
            f"Received layer: {element.layer}"
        )

    evidence_directory = _configured_directory("EVIDENCE_DIR")
    model_repository_directory = _configured_directory("MODEL_REPO_DIR")
    system_id = os.environ.get("MODEL_SYSTEM_ID", "legacy-system")

    for citation in element.evidence:
        _validate_evidence_locator(citation.locator, evidence_directory)

    output_file = (
        model_repository_directory
        / "systems"
        / system_id
        / "as-is"
        / element.layer
        / f"{element.id}.json"
    )

    output_file.parent.mkdir(parents=True, exist_ok=True)

    serialized_element = json.dumps(
        element.model_dump(mode="json"),
        indent=2,
        sort_keys=True,
    ) + "\n"

    if output_file.is_file():
        existing_content = output_file.read_text(encoding="utf-8")

        if existing_content == serialized_element:
            return output_file

    output_file.write_text(serialized_element, encoding="utf-8")

    return output_file


def create_validated_element_writer() -> StructuredTool:
    """
    Create the only tool E1 may use to create model-element JSON.

    The tool validates the D0 schema before writing anything.
    """

    def write_model_element(**element_data: Any) -> str:
        element = ModelElement.model_validate(element_data)
        output_file = persist_strategy_element(element)

        return (
            f"Validated element '{element.id}' written to "
            f"/systems/{os.environ.get('MODEL_SYSTEM_ID', 'legacy-system')}"
            f"/as-is/{element.layer}/{output_file.name}"
        )

    return StructuredTool.from_function(
        func=write_model_element,
        name="write_model_element",
        description=(
            "Validate and persist exactly one Motivation or Strategy ArchiMate "
            "element. Use this only after reading the cited evidence file. "
            "Each evidence locator must be a real path below strategy/ or "
            "motivation/, optionally followed by #Section Name."
        ),
        args_schema=ModelElement,
    )
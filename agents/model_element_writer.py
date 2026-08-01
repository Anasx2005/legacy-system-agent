"""Validated writers for ArchiMate model-element JSON files."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from langchain_core.tools import StructuredTool

from agents.schema import EvidenceCitation, ModelElement


PROJECT_ROOT = Path(__file__).resolve().parent.parent


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


def _validate_evidence_locator(
    locator: str,
    evidence_directory: Path,
    allowed_evidence_folders: set[str],
) -> None:
    """Confirm that an evidence locator points to a permitted real evidence file."""
    file_part = locator.split("#", maxsplit=1)[0].replace("\\", "/")

    if file_part.startswith("/evidence/"):
        file_part = file_part.removeprefix("/evidence/")

    relative_path = Path(file_part)

    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError(f"Unsafe evidence locator: {locator}")

    if not relative_path.parts or relative_path.parts[0] not in allowed_evidence_folders:
        allowed_folders = ", ".join(sorted(allowed_evidence_folders))
        raise ValueError(
            f"Evidence must come from one of: {allowed_folders}. "
            f"Received: {locator}"
        )

    evidence_file = (evidence_directory / relative_path).resolve()

    try:
        evidence_file.relative_to(evidence_directory)
    except ValueError:
        raise ValueError(
            f"Evidence locator escapes the evidence directory: {locator}"
        ) from None

    if not evidence_file.is_file():
        raise ValueError(
            f"Evidence file does not exist for locator: {locator}"
        )


def _canonicalize_evidence_locators(
    element: ModelElement,
    evidence_directory: Path,
    allowed_evidence_folders: set[str],
) -> ModelElement:
    """Add an evidence folder to a bare filename when its location is unique."""
    evidence: list[EvidenceCitation] = []
    for citation in element.evidence:
        locator = citation.locator.replace("\\", "/")
        if locator.startswith("/evidence/"):
            locator = locator.removeprefix("/evidence/")
        elif locator.startswith("evidence/"):
            locator = locator.removeprefix("evidence/")

        file_part = locator.split("#", maxsplit=1)[0]
        if "/" not in file_part:
            matches = [
                folder
                for folder in allowed_evidence_folders
                if (evidence_directory / folder / file_part).is_file()
            ]
            if len(matches) == 1:
                locator = f"{matches[0]}/{locator}"

        evidence.append(citation.model_copy(update={"locator": locator}))
    return element.model_copy(update={"evidence": evidence})


def persist_element(
    element: ModelElement,
    *,
    allowed_layers: set[str],
    allowed_evidence_folders: set[str],
) -> Path:
    """Validate evidence and write one schema-valid element JSON file."""
    if element.layer not in allowed_layers:
        valid_layers = ", ".join(sorted(allowed_layers))
        raise ValueError(
            f"This writer accepts only these layers: {valid_layers}. "
            f"Received: {element.layer}"
        )

    evidence_directory = _configured_directory("EVIDENCE_DIR")
    model_repository_directory = _configured_directory("MODEL_REPO_DIR")
    system_id = os.environ.get("MODEL_SYSTEM_ID", "legacy-system")
    element = _canonicalize_evidence_locators(
        element,
        evidence_directory,
        allowed_evidence_folders,
    )

    for citation in element.evidence:
        _validate_evidence_locator(
            citation.locator,
            evidence_directory,
            allowed_evidence_folders,
        )

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


def _create_element_writer(
    *,
    tool_name: str,
    description: str,
    allowed_layers: set[str],
    allowed_evidence_folders: set[str],
) -> StructuredTool:
    """Create one schema-valid model-element writing tool."""

    def write_element(**element_data: Any) -> str:
        element = ModelElement.model_validate(element_data)

        try:
            output_file = persist_element(
                element,
                allowed_layers=allowed_layers,
                allowed_evidence_folders=allowed_evidence_folders,
            )
        except ValueError as error:
            return f"Element skipped: {error}. Use a real cited evidence file."

        system_id = os.environ.get("MODEL_SYSTEM_ID", "legacy-system")

        return (
            f"Validated element '{element.id}' written to "
            f"/systems/{system_id}/as-is/{element.layer}/{output_file.name}"
        )

    return StructuredTool.from_function(
        func=write_element,
        name=tool_name,
        description=description,
        args_schema=ModelElement,
    )


# E1: Strategy and Motivation writer


def persist_strategy_element(element: ModelElement) -> Path:
    """Write a Motivation or Strategy element backed by approved evidence."""
    return persist_element(
        element,
        allowed_layers={"motivation", "strategy"},
        allowed_evidence_folders={"motivation", "strategy"},
    )


def create_validated_element_writer() -> StructuredTool:
    """Return the E1 writer tool. Kept for strategy_analyst compatibility."""
    return _create_element_writer(
        tool_name="write_model_element",
        description=(
            "Validate and persist one Motivation or Strategy ArchiMate element. "
            "Evidence must refer to a real file under strategy/ or motivation/."
        ),
        allowed_layers={"motivation", "strategy"},
        allowed_evidence_folders={"motivation", "strategy"},
    )


# E2: Business writer


def persist_business_element(element: ModelElement) -> Path:
    """Write a Business element backed by approved business evidence."""
    return persist_element(
        element,
        allowed_layers={"business"},
        allowed_evidence_folders={"business"},
    )


def create_business_element_writer() -> StructuredTool:
    """Return the E2 business-only validated writer tool."""
    return _create_element_writer(
        tool_name="write_business_element",
        description=(
            "Validate and persist one Business ArchiMate element. "
            "Evidence must refer to a real file under business/."
        ),
        allowed_layers={"business"},
        allowed_evidence_folders={"business"},
    )

"""Validated writers for evidence scopes requiring file line-range citations."""

from __future__ import annotations

import re
from typing import Any

from langchain_core.tools import StructuredTool

from agents.model_element_writer import persist_element
from agents.schema import ModelElement


LINE_RANGE_PATTERN = re.compile(
    r"^(?:/evidence/)?(code|infra)/.+#L\d+(?:-L\d+)?$"
)


def _validate_line_range_evidence(
    element: ModelElement,
    expected_folder: str,
) -> None:
    """Require locators such as code/api/routes.py#L10-L24."""
    for citation in element.evidence:
        locator = citation.locator.replace("\\", "/")

        # Accept both:
        # code/file.py#L1-L3
        # evidence/code/file.py#L1-L3
        # /evidence/code/file.py#L1-L3

        if locator.startswith("/evidence/"):
            locator = locator.removeprefix("/evidence/")
        elif locator.startswith("evidence/"):
            locator = locator.removeprefix("evidence/")

        if not locator.startswith(f"{expected_folder}/"):
            raise ValueError(
                f"Evidence must begin with {expected_folder}/. "
                f"Received: {citation.locator}"
            )

        if not LINE_RANGE_PATTERN.fullmatch(locator):
            raise ValueError(
                "Evidence locator must include a line or line range, for example "
                f"{expected_folder}/path/file.py#L10-L24. "
                f"Received: {citation.locator}"
            )


def _create_scoped_element_writer(
    *,
    tool_name: str,
    description: str,
    layer: str,
    allowed_types: set[str],
    evidence_folder: str,
) -> StructuredTool:
    """Create a D0-valid writer restricted to one evidence scope and layer."""

    def write_element(**element_data: Any) -> str:
        element = ModelElement.model_validate(element_data)

        if element.layer != layer:
            raise ValueError(
                f"{tool_name} only accepts the {layer} layer. "
                f"Received: {element.layer}"
            )

        if element.archimate_type not in allowed_types:
            raise ValueError(
                f"{tool_name} does not allow '{element.archimate_type}'. "
                f"Allowed types: {', '.join(sorted(allowed_types))}"
            )

        _validate_line_range_evidence(element, evidence_folder)

        output_file = persist_element(
            element,
            allowed_layers={layer},
            allowed_evidence_folders={evidence_folder},
        )

        return f"Validated element written: {output_file.name}"

    return StructuredTool.from_function(
        func=write_element,
        name=tool_name,
        description=description,
        args_schema=ModelElement,
    )


def create_application_element_writer() -> StructuredTool:
    """Writer used only by E3 code-analyzer."""
    return _create_scoped_element_writer(
        tool_name="write_application_element",
        description=(
            "Validate and write one Application-layer element. Evidence must "
            "reference a real code file and a line range."
        ),
        layer="application",
        allowed_types={
            "Application Component",
            "Application Service",
            "Data Object",
            "Application Interface",
        },
        evidence_folder="code",
    )


def create_technology_element_writer() -> StructuredTool:
    """Writer used only by E4 infra-analyzer."""
    return _create_scoped_element_writer(
        tool_name="write_technology_element",
        description=(
            "Validate and write one Technology-layer element. Evidence must "
            "reference a real infrastructure file and a line range."
        ),
        layer="technology",
        allowed_types={
            "Node",
            "Device",
            "System Software",
            "Technology Service",
            "Artifact",
        },
        evidence_folder="infra",
    )
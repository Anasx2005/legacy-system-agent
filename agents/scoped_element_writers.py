"""Validated writers for evidence scopes requiring file line-range citations."""

from __future__ import annotations

import re
from typing import Any

from langchain_core.tools import StructuredTool

from agents.model_element_writer import persist_element
from agents.schema import EvidenceCitation, ModelElement


LINE_RANGE_PATTERN = re.compile(
    r"^(?:/evidence/)?(code|infra)/.+#L\d+(?:-L\d+)?$"
)


def _canonicalize_line_range_evidence(
    element: ModelElement,
    expected_folder: str,
) -> ModelElement:
    """Validate and canonicalize file citations supplied by scoped analysts.

    The agent filesystem presents ``/evidence/infra/main.tf`` as ``main.tf`` in
    some tool responses.  Preserve strict scope validation while restoring the
    unambiguous configured folder for that bare-file form.
    """
    evidence: list[EvidenceCitation] = []
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

        file_part = locator.split("#", maxsplit=1)[0]
        if "/" not in file_part:
            locator = f"{expected_folder}/{locator}"

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

        evidence.append(citation.model_copy(update={"locator": locator}))

    return element.model_copy(update={"evidence": evidence})


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

        try:
            element = _canonicalize_line_range_evidence(element, evidence_folder)
            output_file = persist_element(
                element,
                allowed_layers={layer},
                allowed_evidence_folders={evidence_folder},
            )
        except ValueError as error:
            # An LLM may propose a plausible-looking but nonexistent file.  It
            # must not bypass validation, but one bad candidate must not abort
            # the entire multi-agent ingestion run.
            return (
                f"Element skipped: {error}. Use a real file under "
                f"{evidence_folder}/ with a line-range locator."
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

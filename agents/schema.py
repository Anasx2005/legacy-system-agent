"""Validated shared contract for ArchiMate elements produced by agents."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


SKILL_PATH = (
    Path(__file__).resolve().parent.parent
    / "skills"
    / "archimate-metamodel"
    / "SKILL.md"
)

LAYER_NAMES = (
    "motivation",
    "strategy",
    "business",
    "application",
    "technology",
)

Layer = Literal["motivation", "strategy", "business", "application", "technology"]
Confidence = Literal["observed", "inferred"]


def _read_table_first_column(section: str) -> set[str]:
    """Return the first data column from a Markdown table."""
    values: set[str] = set()

    for line in section.splitlines():
        line = line.strip()

        if not line.startswith("|"):
            continue

        cells = [cell.strip() for cell in line.strip("|").split("|")]

        # Ignore header rows and Markdown separator rows.
        if not cells or cells[0] in {"Element", "Category"}:
            continue
        if all(set(cell) <= {"-", ":"} for cell in cells):
            continue

        values.add(cells[0])

    return values


@lru_cache
def load_archimate_types_by_layer() -> dict[str, set[str]]:
    """
    Parse valid ArchiMate element names from the project's metamodel skill.

    The SKILL.md file remains the single source of truth.
    """
    if not SKILL_PATH.is_file():
        raise RuntimeError(f"ArchiMate skill was not found: {SKILL_PATH}")

    skill_text = SKILL_PATH.read_text(encoding="utf-8")

    section_pattern = re.compile(
        r"^### 1\.(?P<number>[1-5]) .*?(?=^### 1\.[1-5] |^## 2\.|\Z)",
        re.MULTILINE | re.DOTALL,
    )

    section_to_layer = {
        "1": "motivation",
        "2": "strategy",
        "3": "business",
        "4": "application",
        "5": "technology",
    }

    types_by_layer: dict[str, set[str]] = {
        layer: set() for layer in LAYER_NAMES
    }

    for match in section_pattern.finditer(skill_text):
        layer = section_to_layer[match.group("number")]
        types_by_layer[layer] = _read_table_first_column(match.group(0))

    if not all(types_by_layer.values()):
        raise RuntimeError(
            "Could not parse all ArchiMate element tables from "
            f"{SKILL_PATH}. Check the SKILL.md heading/table format."
        )

    return types_by_layer


@lru_cache
def load_relationship_types() -> set[str]:
    """Parse supported relationship names from section 2 of the skill."""
    if not SKILL_PATH.is_file():
        raise RuntimeError(f"ArchiMate skill was not found: {SKILL_PATH}")

    skill_text = SKILL_PATH.read_text(encoding="utf-8")

    match = re.search(
        r"^## 2\. Relationship Types.*?(?=^## 3\.|\Z)",
        skill_text,
        re.MULTILINE | re.DOTALL,
    )
    if not match:
        raise RuntimeError("Could not find relationship types in SKILL.md.")

    relationships: set[str] = set()

    for line in match.group(0).splitlines():
        line = line.strip()

        if not line.startswith("|"):
            continue

        cells = [cell.strip() for cell in line.strip("|").split("|")]

        # Table is: Category | Relationship | Definition
        if len(cells) < 2 or cells[0] == "Category":
            continue
        if all(set(cell) <= {"-", ":"} for cell in cells):
            continue

        relationships.add(cells[1])

    if not relationships:
        raise RuntimeError("No ArchiMate relationship types were parsed.")

    return relationships


class EvidenceCitation(BaseModel):
    """Evidence supporting one extracted model element."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_type: str = Field(min_length=1)
    locator: str = Field(min_length=1)


class Relationship(BaseModel):
    """A relationship from the current element to another element."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    target_id: str = Field(
        min_length=1,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        description="Stable, human-readable slug of the target element.",
    )
    type: str = Field(min_length=1)

    @field_validator("type")
    @classmethod
    def relationship_type_must_exist_in_skill(cls, value: str) -> str:
        if value not in load_relationship_types():
            valid_types = ", ".join(sorted(load_relationship_types()))
            raise ValueError(
                f"Unknown ArchiMate relationship type '{value}'. "
                f"Valid types: {valid_types}"
            )
        return value


class ModelElement(BaseModel):
    """
    Shared output contract for every ingestion subagent.

    This is the only format that agents may send to the reconciler,
    validator, database writer, or Git writer.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(
        min_length=1,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        description="Stable, human-readable slug.",
    )
    layer: Layer
    archimate_type: str = Field(min_length=1)
    name: str = Field(min_length=1)
    documentation: str = Field(min_length=1)
    confidence: Confidence
    evidence: list[EvidenceCitation] = Field(
        min_length=1,
        description="At least one traceable source is mandatory.",
    )
    relationships: list[Relationship] = Field(default_factory=list)

    @model_validator(mode="after")
    def archimate_type_must_match_the_skill_and_layer(self) -> "ModelElement":
        valid_types_by_layer = load_archimate_types_by_layer()
        valid_types = valid_types_by_layer[self.layer]

        if self.archimate_type not in valid_types:
            known_layers = [
                layer
                for layer, types in valid_types_by_layer.items()
                if self.archimate_type in types
            ]

            if known_layers:
                raise ValueError(
                    f"'{self.archimate_type}' is not valid in layer "
                    f"'{self.layer}'. It belongs to: {', '.join(known_layers)}."
                )

            all_types = sorted(
                element_type
                for types in valid_types_by_layer.values()
                for element_type in types
            )
            raise ValueError(
                f"Unknown ArchiMate type '{self.archimate_type}'. "
                f"Valid types: {', '.join(all_types)}"
            )

        return self
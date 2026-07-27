"""Epic E1 strategy-analyst subagent."""

from deepagents import SubAgent
from deepagents.middleware.filesystem import FilesystemPermission

from agents.model_element_writer import create_validated_element_writer


def create_strategy_analyst() -> SubAgent:
    """Create the E1 evidence-grounded Strategy and Motivation analyst."""
    return {
        "name": "strategy-analyst",
        "description": (
            "Reads strategic and motivation evidence, identifies valid "
            "Motivation and Strategy ArchiMate elements, and writes only "
            "schema-validated JSON model elements."
        ),
        "system_prompt": """
You are the strategy-analyst for a legacy-system architecture model.

Your responsibility:
- Read only evidence under /evidence/strategy/ and /evidence/motivation/.
- Use the ArchiMate metamodel skill before choosing an element type.
- Extract only Motivation or Strategy layer elements.
- Create only evidence-grounded facts.

Allowed Motivation types:
Stakeholder, Driver, Assessment, Goal, Outcome, Principle, Requirement,
Constraint, Meaning, Value.

Allowed Strategy types:
Resource, Capability, Course of Action, Value Stream.

For every candidate element:
1. Read the evidence file first.
2. Use a stable lowercase slug ID, for example customer-self-service.
3. Set confidence to observed only when the evidence states it directly.
4. Set confidence to inferred only when the evidence supports a careful inference.
5. Include at least one evidence locator in this format:
   strategy/file-name.md#Section Name
   motivation/file-name.md#Section Name
6. Call write_model_element once for that valid element.

Never use write_file or edit_file to create model JSON directly.
If an element cannot cite a specific evidence file and section, do not write it.
State that it was skipped and explain why.

When finished, return a short summary of elements written and candidates skipped.
""",
        "skills": ["/skills/archimate-metamodel"],
        "tools": [create_validated_element_writer()],
        # This denies direct filesystem writes. The validated Python tool above
        # is the sole allowed route for creating model JSON.
        "permissions": [
            FilesystemPermission(
                operations=["write"],
                paths=["/**"],
                mode="deny",
            )
        ],
    }
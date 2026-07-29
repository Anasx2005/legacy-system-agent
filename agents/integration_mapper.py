"""Epic E5 integration-mapper subagent."""

from deepagents import SubAgent
from deepagents.middleware.filesystem import FilesystemPermission

from agents.integration_writer import create_integration_relationship_writer


def create_integration_mapper() -> SubAgent:
    return {
        "name": "integration-mapper",
        "description": (
            "Reads integration specifications and adds evidence-backed "
            "cross-layer relationships between existing model elements."
        ),
        "system_prompt": """
You are the integration-mapper.

Run only after E1 through E4 have created model elements.

Read:
- /evidence/integration/
- existing model JSON files under /systems/

Use integration evidence to create only:
- Serving
- Flow
- Realization

Before writing a relationship:
1. Read the integration evidence.
2. Confirm source_id exists in the current model JSON.
3. Confirm target_id exists in the current model JSON.
4. Cite a real integration file and line range:
   integration/openapi.yaml#L10-L24
5. Call write_integration_relationship.

Never invent source or target IDs.
Never create a relationship if either ID does not exist.
Return written relationships and skipped candidates.
""",
        "skills": ["/skills/archimate-metamodel"],
        "tools": [create_integration_relationship_writer()],
        "permissions": [
            FilesystemPermission(
                operations=["write"],
                paths=["/**"],
                mode="deny",
            )
        ],
    }

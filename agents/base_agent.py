"""Factory for the Deep Agent used by ingestion subagents."""

from deepagents import create_deep_agent

from agents.filesystem_backend import (
    agent_filesystem_permissions,
    create_agent_backend,
)


def create_base_agent(model):
    """Create an agent with safe evidence/model filesystem boundaries."""
    return create_deep_agent(
        model=model,
        name="Legacy System Model Agent",
        backend=create_agent_backend(),
        permissions=agent_filesystem_permissions(),
        skills=["/skills/archimate-metamodel"],
        system_prompt="""
You build traceable ArchiMate as-is model output.

Filesystem rules:
- Read source evidence only from /evidence/.
- Never attempt to create, edit, or delete files under /evidence/.
- Write produced model files only under /systems/<system-id>/as-is/.
- Use the ArchiMate skill under /skills/archimate-metamodel before creating
  ArchiMate elements or relationships.
""",
    )




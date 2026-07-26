"""Factory for the base Deep Agent."""

from deepagents import create_deep_agent

from agents.filesystem_backend import (
    agent_filesystem_permissions,
    create_agent_backend,
)
from backend.llms.groq import get_llm


def create_base_agent():
    """Create the MVP base Deep Agent using Groq."""
    return create_deep_agent(
        model=get_llm(),
        name="Legacy System Model Agent",
        backend=create_agent_backend(),
        permissions=agent_filesystem_permissions(),
        skills=["/skills/archimate-metamodel"],
        system_prompt="""
You are the base agent for a legacy-system modelling platform.
Respond clearly and use the filesystem only when needed.
""",
    )
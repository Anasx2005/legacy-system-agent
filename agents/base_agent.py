"""Factory for the base Deep Agent."""

from deepagents import create_deep_agent

from agents.filesystem_backend import (
    agent_filesystem_permissions,
    create_agent_backend,
)
from agents.stub_subagents import create_stub_subagents
from backend.llms.groq import get_llm


def create_base_agent():
    """Create the MVP Deep Agent with D3 placeholder subagents."""
    return create_deep_agent(
        model=get_llm(),
        name="Legacy System Model Agent",
        backend=create_agent_backend(),
        permissions=agent_filesystem_permissions(),
        skills=["/skills/archimate-metamodel"],
        subagents=create_stub_subagents(),
        system_prompt="""
You are the orchestrator for a legacy-system modelling platform.

When asked to test delegation, use the task tool and select the requested
subagent type. Never invent subagent results yourself; report only the result
returned by each subagent.
""",
    )
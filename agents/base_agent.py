"""Factory for the base Deep Agent."""

from deepagents import create_deep_agent

from agents.filesystem_backend import (
    agent_filesystem_permissions,
    create_agent_backend,
)
from agents.strategy_analyst import create_strategy_analyst
from agents.stub_subagents import create_stub_subagents
from backend.llms.ollama_cloud import get_llm




def create_subagents():
    """Use the real E1 analyst and retain placeholders for future Epic E work."""
    placeholder_subagents = [
        subagent
        for subagent in create_stub_subagents()
        if subagent["name"] != "strategy-analyst"
    ]

    return [create_strategy_analyst(), *placeholder_subagents]





def create_base_agent():
    """Create the MVP Deep Agent with D3 placeholder subagents."""
    return create_deep_agent(
        model=get_llm(),
        name="Legacy System Model Agent",
        backend=create_agent_backend(),
        permissions=agent_filesystem_permissions(),
        skills=["/skills/archimate-metamodel"],
        subagents=[create_strategy_analyst()],
        system_prompt="""
You are the orchestrator for a legacy-system modelling platform.

When asked to test delegation, use the task tool and select the requested
subagent type. Never invent subagent results yourself; report only the result
returned by each subagent.
""",
    )
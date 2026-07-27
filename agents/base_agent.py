"""Factory for the base Deep Agent."""

from deepagents import create_deep_agent

from agents.filesystem_backend import (
    agent_filesystem_permissions,
    create_agent_backend,
)
from agents.strategy_analyst import create_strategy_analyst
from agents.business_analyst import create_business_analyst
from agents.stub_subagents import create_stub_subagents
from backend.llms.ollama_cloud import get_llm

from agents.business_analyst import create_business_analyst
from agents.code_analyzer import create_code_analyzer
from agents.infra_analyzer import create_infra_analyzer
from agents.integration_mapper import create_integration_mapper
from agents.strategy_analyst import create_strategy_analyst




def create_subagents():
    """Register all implemented Epic E subagents."""
    return [
        create_strategy_analyst(),
        create_business_analyst(),
        create_code_analyzer(),
        create_infra_analyzer(),
        create_integration_mapper(),
    ]


def create_base_agent():
    """Create the MVP Deep Agent with D3 placeholder subagents."""
    return create_deep_agent(
        model=get_llm(),
        name="Legacy System Model Agent",
        backend=create_agent_backend(),
        permissions=agent_filesystem_permissions(),
        skills=["/skills/archimate-metamodel"],
        subagents=create_subagents(),
        system_prompt="""
You are the orchestrator for a legacy-system modelling platform.

When asked to test delegation, use the task tool and select the requested
subagent type. Never invent subagent results yourself; report only the result
returned by each subagent.
""",
    )
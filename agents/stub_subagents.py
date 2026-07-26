"""Temporary subagents used only to verify D3 delegation wiring."""

from deepagents import SubAgent


STUB_RESPONSE = "stub–ok"

SUBAGENT_NAMES = (
    "strategy-analyst",
    "business-analyst",
    "code-analyzer",
    "infra-analyzer",
    "integration-mapper",
)


def create_stub_subagents() -> list[SubAgent]:
    """Return the five placeholder agents required for D3."""
    return [
        {
            "name": name,
            "description": (
                f"D3 placeholder for {name}. "
                "Use this only to verify delegation wiring."
            ),
            "system_prompt": f"""
You are a temporary D3 placeholder subagent.

Ignore the task content and do not use tools.
Your entire final response must be exactly this text:

{STUB_RESPONSE}

Do not add punctuation, explanations, Markdown, or any other words.
""",
            # Do not add project-specific external tools during this smoke test.
            "tools": [],
            # The real Epic E agents will receive the ArchiMate skill if needed.
            "skills": [],
        }
        for name in SUBAGENT_NAMES
    ]
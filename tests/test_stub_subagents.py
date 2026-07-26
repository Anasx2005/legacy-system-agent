from agents.stub_subagents import (
    STUB_RESPONSE,
    SUBAGENT_NAMES,
    create_stub_subagents,
)


def test_all_five_placeholder_subagents_are_registered():
    subagents = create_stub_subagents()

    assert [subagent["name"] for subagent in subagents] == list(SUBAGENT_NAMES)
    assert len(subagents) == 5


def test_each_placeholder_requires_the_stub_response():
    for subagent in create_stub_subagents():
        assert STUB_RESPONSE in subagent["system_prompt"]
        assert subagent["tools"] == []
        assert subagent["skills"] == []
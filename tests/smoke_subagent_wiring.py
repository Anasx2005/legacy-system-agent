from agents.base_agent import create_base_agent


PROMPT = """
This is a delegation wiring test.

You must use the task tool to call every one of these subagent types:

1. strategy-analyst
2. business-analyst
3. code-analyzer
4. infra-analyzer
5. integration-mapper

Call each subagent exactly once. Ask each one to return its required literal
response.

After all five task-tool calls finish, return a numbered list showing the
response received from each subagent. Do not create the responses yourself.
"""


def message_text(message) -> str:
    """Return readable text whether the model uses string or block content."""
    if isinstance(message.content, str):
        return message.content

    if isinstance(message.content, list):
        return "\n".join(
            block["text"]
            for block in message.content
            if isinstance(block, dict) and block.get("type") == "text"
        )

    return str(message.content)


def main():
    agent = create_base_agent()

    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": PROMPT,
                }
            ]
        }
    )

    print(message_text(result["messages"][-1]))


if __name__ == "__main__":
    main()
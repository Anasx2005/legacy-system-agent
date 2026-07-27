from agents.base_agent import create_base_agent


PROMPT = """
Delegate this task to strategy-analyst:

Read every document in /evidence/strategy/ and /evidence/motivation/.
Use the ArchiMate skill to identify valid Motivation and Strategy elements.

Write each evidence-grounded element using write_model_element.
Do not write elements without a specific evidence file and section locator.

When the subagent finishes, report its summary exactly as returned.
"""


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

    print(result["messages"][-1].content)


if __name__ == "__main__":
    main()
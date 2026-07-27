from agents.base_agent import create_base_agent


PROMPT = """
Delegate this task to business-analyst.

Read every file under /evidence/business/.
Use the ArchiMate skill to identify supported Business-layer elements.

Write each evidence-grounded element using write_business_element.
Do not create elements without a specific business evidence file and section.

When complete, report the business-analyst summary.
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
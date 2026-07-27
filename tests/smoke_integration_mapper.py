from agents.base_agent import create_base_agent


def main():
    agent = create_base_agent()

    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Delegate to integration-mapper. Read "
                        "/evidence/integration/ and current element JSON files "
                        "under /systems/. Add only evidence-backed Serving, "
                        "Flow, or Realization relationships between existing IDs."
                    ),
                }
            ]
        }
    )

    print(result["messages"][-1].content)


if __name__ == "__main__":
    main()
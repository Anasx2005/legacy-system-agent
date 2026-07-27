from agents.base_agent import create_base_agent


def main():
    agent = create_base_agent()

    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Delegate to code-analyzer. Read /evidence/code/, "
                        "discover relevant files with glob and grep, then "
                        "write evidence-grounded Application elements."
                    ),
                }
            ]
        }
    )

    print(result["messages"][-1].content)


if __name__ == "__main__":
    main()
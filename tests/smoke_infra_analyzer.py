from agents.base_agent import create_base_agent


def main():
    agent = create_base_agent()

    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Delegate to infra-analyzer. Read /evidence/infra/, "
                        "use glob and grep before reading files, then write "
                        "evidence-grounded Technology elements."
                    ),
                }
            ]
        }
    )

    print(result["messages"][-1].content)


if __name__ == "__main__":
    main()
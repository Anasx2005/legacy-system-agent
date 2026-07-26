from agents.base_agent import create_base_agent


def main():
    agent = create_base_agent()

    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "Hello. Reply with one short sentence. and tell me the permission that you have in backend sysytems and whats is the skill that you have ",
                }
            ]
        }
    )

    print(result["messages"][-1].content)


if __name__ == "__main__":
    main()
from agents.base_agent import create_base_agent
from backend.llms.groq import get_llm


agent = create_base_agent(get_llm())

result = agent.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": """
Perform these actions exactly:

1. Read /evidence/sample-legacy-code.txt.
2. Try to create /evidence/forbidden.txt with the text "this must fail".
3. Create /systems/legacy-system/as-is/application/test-output.md
   with the text "# D1 filesystem smoke test".
4. Report the result of each action.
""",
            }
        ]
    }
)

print(result["messages"][-1].content)
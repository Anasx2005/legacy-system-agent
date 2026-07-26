from backend.llms.gemini import get_llm
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

agent = create_deep_agent(
    model=get_llm(),
    backend=FilesystemBackend(
        root_dir=r"D:\Legacy-System-Agent",
        virtual_mode=True,
    ),
    skills=["/skills/"],
)

result = agent.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": "What layer does Application Interface belong to?",
            }
        ]
    }
)

print(type(result))
print(result)
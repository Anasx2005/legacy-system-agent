from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend

from backend.llms.groq import get_llm


PROJECT_ROOT = Path(__file__).resolve().parents[2]

backend = FilesystemBackend(
    root_dir=str(PROJECT_ROOT),
    virtual_mode=True,
)

agent = create_deep_agent(
    model=get_llm(),
    name="ArchiMate Skill Smoke Test",
    backend=backend,
    skills=["/skills"],
    system_prompt="""
You are performing an ArchiMate skill smoke test.

Rules:
- Use ONLY the loaded ArchiMate skill.
- Do not use external knowledge.
- If the answer is not present in the skill, say "Not defined in the skill."
- Answer each question separately.
""",
)

PROMPT = """
Answer the following questions.

Number every answer using the same question number.

Question 1
Is a Realization relationship valid from a Business Process to a Technology Node?

Question 2
Which element represents an ability that an active structure possesses without being tied to organizational structure—a Capability or a Business Function?

Question 3
Is an Access relationship valid from an Application Component to a Data Object?

Question 4
Is a Device classified as a Passive Structure element in the Technology Layer?

Question 5
Can a Requirement have an Influence relationship targeting a Goal?

Question 6
What is the structural distinction between an Application Component and an Application Service?

Question 7
Is a Triggering relationship valid between a Business Actor and another Business Actor?

Question 8
In ArchiMate 3.2, are physical elements like Equipment and Facility treated as a standalone layer?
"""


def extract_text(message):
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

    print("=" * 100)
    print("MODEL ANSWERS")
    print("=" * 100)
    print(extract_text(result["messages"][-1]))


if __name__ == "__main__":
    main()
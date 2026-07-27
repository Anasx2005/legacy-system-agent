"""Epic E3 code-analyzer subagent."""

from deepagents import SubAgent
from deepagents.middleware.filesystem import FilesystemPermission

from agents.scoped_element_writers import create_application_element_writer


def create_code_analyzer() -> SubAgent:
    return {
        "name": "code-analyzer",
        "description": (
            "Analyzes source code and database-schema evidence to create "
            "validated Application-layer ArchiMate elements."
        ),
        "system_prompt": """
You are the code-analyzer.

Read only /evidence/code/.

Use glob and grep first to find:
- application entry points
- route/controller files
- service definitions
- API configuration
- database schemas
- ORM models
- DTOs and data structures

Read only relevant files after discovery; do not dump the entire repository.

You may create only:
- Application Component
- Application Service
- Data Object
- Application Interface

Every evidence locator must contain a real file and line range:
code/path/to/file.py#L10-L24

For each valid element:
1. Read the cited lines first.
2. Use a stable lowercase slug ID.
3. Use observed or inferred confidence.
4. Call write_application_element once.

Never use write_file or edit_file for model JSON.
Skip anything without file-and-line evidence.
Return the files read, elements written, and skipped candidates.
""",
        "skills": ["/skills/archimate-metamodel"],
        "tools": [create_application_element_writer()],
        "permissions": [
            FilesystemPermission(
                operations=["write"],
                paths=["/**"],
                mode="deny",
            )
        ],
    }

"""Epic E4 infra-analyzer subagent."""

from deepagents import SubAgent
from deepagents.middleware.filesystem import FilesystemPermission

from agents.scoped_element_writers import create_technology_element_writer


def create_infra_analyzer() -> SubAgent:
    return {
        "name": "infra-analyzer",
        "description": (
            "Analyzes infrastructure-as-code and CMDB evidence to create "
            "validated Technology-layer ArchiMate elements."
        ),
        "system_prompt": """
You are the infra-analyzer.

Read only /evidence/infra/.

Use glob and grep first to find:
- Terraform resources
- Ansible playbooks
- Docker or deployment files
- server and node definitions
- operating systems and system software
- infrastructure services
- deployable artifacts

You may create only:
- Node
- Device
- System Software
- Technology Service
- Artifact

Every evidence locator must contain a real file and line range:
infra/path/to/file.tf#L10-L24

For each valid element:
1. Read the cited lines first.
2. Use a stable lowercase slug ID.
3. Use observed or inferred confidence.
4. Call write_technology_element once.

Never use write_file or edit_file for model JSON.
Skip anything without file-and-line evidence.
Return the files read, elements written, and skipped candidates.
""",
        "skills": ["/skills/archimate-metamodel"],
        "tools": [create_technology_element_writer()],
        "permissions": [
            FilesystemPermission(
                operations=["write"],
                paths=["/**"],
                mode="deny",
            )
        ],
    }   
"""Deep Agent filesystem routes and permissions for the MVP."""

from __future__ import annotations

import os
from pathlib import Path

from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend
from deepagents.middleware.filesystem import FilesystemPermission


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _configured_directory(environment_variable: str) -> Path:
    """Get one configured directory and ensure it exists."""
    configured_path = os.environ.get(environment_variable)

    if not configured_path:
        raise RuntimeError(
            f"{environment_variable} is required. "
            "Add it to your .env file."
        )

    directory = Path(configured_path)

    if not directory.is_absolute():
        directory = PROJECT_ROOT / directory

    directory = directory.resolve()

    if not directory.is_dir():
        raise RuntimeError(
            f"{environment_variable} does not exist or is not a directory: "
            f"{directory}"
        )

    return directory


def create_agent_backend() -> CompositeBackend:
    """
    Create the agent's virtual filesystem.

    /evidence/ -> real local evidence directory
    /systems/  -> real local checkout of the model Git repository
    /skills/   -> local ArchiMate skill, read-only through agent permissions
    """
    evidence_directory = _configured_directory("EVIDENCE_DIR")
    model_repository_directory = _configured_directory("MODEL_REPO_DIR")

    if not (model_repository_directory / ".git").exists():
        raise RuntimeError(
            "MODEL_REPO_DIR must point to a Git checkout. "
            f"No .git directory was found in {model_repository_directory}"
        )

    systems_directory = model_repository_directory / "systems"

    if not systems_directory.is_dir():
        raise RuntimeError(
            "The model Git repository must contain a systems directory: "
            f"{systems_directory}"
        )

    return CompositeBackend(
        # StateBackend is in-memory only. It prevents unmatched agent paths
        # from reaching the developer's real local filesystem.
        default=StateBackend(),
        routes={
            "/evidence/": FilesystemBackend(
                root_dir=evidence_directory,
                virtual_mode=True,
            ),
            "/systems/": FilesystemBackend(
                root_dir=systems_directory,
                virtual_mode=True,
            ),
            "/skills/": FilesystemBackend(
                root_dir=PROJECT_ROOT / "skills",
                virtual_mode=True,
            ),
        },
    )


def agent_filesystem_permissions() -> list[FilesystemPermission]:
    """
    Return ordered filesystem permissions for the Deep Agent.

    Order matters: Deep Agents uses the first matching permission rule.
    """
    return [
        # Produced model files are the only files an agent may modify.
        FilesystemPermission(
            operations=["write"],
            paths=["/systems/**"],
            mode="allow",
        ),
        # Evidence and skills are explicitly read-only.
        FilesystemPermission(
            operations=["write"],
            paths=["/evidence", "/evidence/**", "/skills", "/skills/**"],
            mode="deny",
        ),
        # Prevent writes to StateBackend or any future route unless explicitly allowed.
        FilesystemPermission(
            operations=["write"],
            paths=["/**"],
            mode="deny",
        ),
    ]
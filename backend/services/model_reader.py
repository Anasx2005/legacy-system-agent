"""Read approved model content directly from the model repository's main branch."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _model_repo_dir() -> Path:
    configured = os.getenv("MODEL_REPO_DIR")
    if not configured:
        raise RuntimeError("MODEL_REPO_DIR is not configured.")
    path = Path(configured)
    return (path if path.is_absolute() else PROJECT_ROOT / path).resolve()


def read_model_element_from_main(git_path: str) -> dict[str, Any]:
    path = Path(git_path.replace("/", "\\"))
    if path.is_absolute() or ".." in path.parts or path.parts[:1] != ("systems",):
        raise ValueError("Unsafe model git path.")

    repo_dir = _model_repo_dir()
    fetch = subprocess.run(
        ["git", "fetch", "origin", "main"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    if fetch.returncode != 0:
        raise RuntimeError(fetch.stderr.strip() or "Could not fetch origin/main.")

    shown = subprocess.run(
        ["git", "show", f"origin/main:{git_path}"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    if shown.returncode != 0:
        raise FileNotFoundError(git_path)
    return json.loads(shown.stdout)

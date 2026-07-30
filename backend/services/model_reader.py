"""Read approved model content directly from the model repository's main branch."""

from __future__ import annotations

import json
import os
import re
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


def _evidence_excerpt(locator: str) -> str | None:
    """Return a short, safe source excerpt for a model evidence locator."""
    configured = os.getenv("EVIDENCE_DIR")
    if not configured:
        return None
    evidence_root = Path(configured)
    evidence_root = (
        evidence_root if evidence_root.is_absolute() else PROJECT_ROOT / evidence_root
    ).resolve()
    relative, _, anchor = locator.partition("#")
    candidate = (evidence_root / relative).resolve()
    try:
        candidate.relative_to(evidence_root)
    except ValueError:
        return None
    if not candidate.is_file():
        return None

    lines = candidate.read_text(encoding="utf-8", errors="replace").splitlines()
    line_range = re.fullmatch(r"L(\d+)(?:-L?(\d+))?", anchor)
    if line_range:
        start = max(int(line_range.group(1)) - 1, 0)
        end = int(line_range.group(2) or line_range.group(1))
        excerpt = "\n".join(lines[start:end])
    elif anchor:
        heading = next(
            (
                index
                for index, line in enumerate(lines)
                if anchor.lower() in line.lower()
            ),
            None,
        )
        if heading is None:
            return None
        end = next(
            (
                index
                for index in range(heading + 1, len(lines))
                if lines[index].startswith("#")
            ),
            len(lines),
        )
        excerpt = "\n".join(lines[heading:end])
    else:
        excerpt = "\n".join(lines[:20])
    return excerpt[:800] or None


def _add_evidence_excerpts(element: dict[str, Any]) -> dict[str, Any]:
    for citation in element.get("evidence", []):
        if isinstance(citation, dict) and isinstance(citation.get("locator"), str):
            citation["excerpt"] = _evidence_excerpt(citation["locator"])
    return element


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
    return _add_evidence_excerpts(json.loads(shown.stdout))

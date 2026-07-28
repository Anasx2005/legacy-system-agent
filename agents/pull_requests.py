"""Deterministic GitHub PR automation for Epic G2."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from backend.repository.artifact_version_repository import (
    get_artifact_version_by_run,
    save_pending_artifact_version,
)


def github_request(
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> Any:
    token = os.getenv("GITHUB_TOKEN")

    if not token:
        raise RuntimeError("GITHUB_TOKEN is not configured.")

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Legacy-System-Agent",
    }

    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        f"https://api.github.com{path}",
        data=data,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else None

    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"GitHub API request failed with HTTP {error.code}: {body}"
        ) from None

    except urllib.error.URLError as error:
        raise RuntimeError(
            f"GitHub API connection failed: {error.reason}"
        ) from None


def read_validator_report(system_id: str) -> dict[str, Any]:
    repo_dir = Path(os.environ["MODEL_REPO_DIR"]).resolve()

    report_path = (
        repo_dir
        / "systems"
        / system_id
        / "as-is"
        / "validation-report.json"
    )

    if not report_path.exists():
        raise RuntimeError(f"Validator report not found: {report_path}")

    report = json.loads(report_path.read_text(encoding="utf-8"))

    if report.get("overall_status", "").upper() != "PASS":
        raise RuntimeError(
            "Validator report is not PASS; G2 will not create a PR."
        )

    return report


def markdown_safe(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", "")


def build_pr_body(
    *,
    system_id: str,
    run_id: str,
    commit_sha: str,
    report: dict[str, Any],
) -> str:
    counts = report.get("element_counts", {})
    conflicts = report.get("conflicts", [])
    errors = report.get("errors", [])
    warnings = report.get("warnings", [])

    lines = [
        "# Automated Architecture Model Recovery",
        "",
        f"- **System ID:** `{system_id}`",
        f"- **Run ID:** `{run_id}`",
        f"- **Commit SHA:** `{commit_sha}`",
        f"- **Generated at:** `{datetime.now(UTC).isoformat()}`",
        "",
        "## Validator Summary",
        f"- Total elements: **{report.get('total_elements', 0)}**",
        f"- Total relationships: **{report.get('total_relationships', 0)}**",
        f"- Validation errors: **{len(errors)}**",
        f"- Validation warnings: **{len(warnings)}**",
        "",
        "## Element Count by Layer",
        "| Layer | Elements |",
        "| --- | ---: |",
    ]

    for layer, count in sorted(counts.items()):
        lines.append(f"| {markdown_safe(layer)} | {markdown_safe(count)} |")

    lines.extend(["", "## Flagged Conflicts"])

    if conflicts:
        for conflict in conflicts:
            lines.append(f"- {markdown_safe(conflict)}")
    else:
        lines.append("- No conflicts were reported by validation.")

    lines.extend(
        [
            "",
            "---",
            "This pull request was created deterministically by Epic G2.",
        ]
    )

    return "\n".join(lines)


def find_existing_pr(
    *,
    repository: str,
    owner: str,
    branch_name: str,
) -> dict[str, Any] | None:
    query = urllib.parse.urlencode(
        {
            "state": "all",
            "head": f"{owner}:{branch_name}",
        }
    )

    prs = github_request(
        "GET",
        f"/repos/{repository}/pulls?{query}",
    )

    return prs[0] if prs else None


def open_pull_request(
    *,
    db: Session,
    system_db_id: int,
    system_id: str,
    run_id: str,
    commit_sha: str,
) -> dict[str, Any]:
    """Open or recover one PR, then persist one pending artifact version."""
    if not commit_sha:
        raise ValueError("commit_sha is required.")

    repository = os.getenv("GITHUB_MODEL_REPO")
    if not repository or "/" not in repository:
        raise RuntimeError(
            "GITHUB_MODEL_REPO must be in owner/repository format."
        )

    existing_artifact = get_artifact_version_by_run(
        db=db,
        system_id=system_db_id,
        run_id=run_id,
    )

    if existing_artifact and existing_artifact.pr_number:
        return {
            "status": "already_created",
            "pr_number": existing_artifact.pr_number,
            "commit_sha": existing_artifact.commit_sha,
            "approval_status": existing_artifact.approval_status,
        }

    report = read_validator_report(system_id)
    branch_name = f"feature/ingest-{system_id}-{run_id}"
    owner = repository.split("/", maxsplit=1)[0]

    existing_pr = find_existing_pr(
        repository=repository,
        owner=owner,
        branch_name=branch_name,
    )

    if existing_pr:
        pr = existing_pr
        status = "recovered_existing_pr"
    else:
        pr = github_request(
            "POST",
            f"/repos/{repository}/pulls",
            {
                "title": (
                    f"feat(model): ingest {system_id} "
                    f"[run_id: {run_id}]"
                ),
                "head": branch_name,
                "base": "main",
                "body": build_pr_body(
                    system_id=system_id,
                    run_id=run_id,
                    commit_sha=commit_sha,
                    report=report,
                ),
            },
        )
        status = "created"

    artifact = save_pending_artifact_version(
        db,
        system_id=system_db_id,
        run_id=run_id,
        commit_sha=commit_sha,
        pr_number=pr["number"],
    )

    return {
        "status": status,
        "pr_number": pr["number"],
        "pr_url": pr["html_url"],
        "commit_sha": artifact.commit_sha,
        "approval_status": artifact.approval_status,
        "artifact_version_id": artifact.id,
    }
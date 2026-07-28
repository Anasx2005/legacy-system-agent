"""Secure GitHub PR-merge webhook receiver for Epic G3."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database.models.artifact_version import ArtifactVersion
from backend.database.models.model_element_index import ModelElementIndex
from backend.database.models.webhook_delivery import WebhookDelivery
from backend.database.session import get_db


router = APIRouter(prefix="/webhooks", tags=["webhooks"])

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def verify_github_signature(
    raw_body: bytes,
    signature: str | None,
    secret: str | None,
) -> bool:
    """Verify GitHub's X-Hub-Signature-256 using a constant-time comparison."""
    if not secret:
        return False

    if not signature or not signature.startswith("sha256="):
        return False

    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


def git(repo_dir: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"Git command failed: git {' '.join(args)}\n{message}")

    return result.stdout.strip()


def read_merged_elements_from_main(
    *,
    system_id: str,
    merge_commit_sha: str,
) -> list[dict[str, Any]]:
    """
    Read element JSON files directly from origin/main.
    This never trusts the currently checked-out local branch.
    """
    configured_path = os.getenv("MODEL_REPO_DIR")
    if not configured_path:
        raise RuntimeError("MODEL_REPO_DIR is not configured.")

    repo_dir = Path(configured_path)
    if not repo_dir.is_absolute():
        repo_dir = PROJECT_ROOT / repo_dir

    repo_dir = repo_dir.resolve()

    git(repo_dir, ["fetch", "origin", "main"])

    model_root = f"systems/{system_id}/as-is"

    paths = git(
        repo_dir,
        ["ls-tree", "-r", "--name-only", "origin/main", "--", model_root],
    ).splitlines()

    elements: list[dict[str, Any]] = []

    for git_path in paths:
        if not git_path.endswith(".json"):
            continue

        if git_path.endswith(
            ("validation-report.json", "reconciliation-report.json")
        ):
            continue

        raw_json = git(
            repo_dir,
            ["show", f"origin/main:{git_path}"],
        )

        try:
            element = json.loads(raw_json)
        except json.JSONDecodeError as error:
            raise RuntimeError(
                f"Invalid element JSON in merged main branch: {git_path}"
            ) from error

        required_fields = ("layer", "archimate_type", "name")
        if not all(element.get(field) for field in required_fields):
            raise RuntimeError(
                f"Element is missing required index fields: {git_path}"
            )

        elements.append(
            {
                "git_path": git_path,
                "layer": element["layer"],
                "archimate_type": element["archimate_type"],
                "name": element["name"],
                "current_commit": merge_commit_sha,
            }
        )

    return elements


def rebuild_model_element_index(
    *,
    db: Session,
    system_db_id: int,
    system_id: str,
    merge_commit_sha: str,
) -> int:
    """Replace the index with the content actually present in origin/main."""
    elements = read_merged_elements_from_main(
        system_id=system_id,
        merge_commit_sha=merge_commit_sha,
    )

    db.execute(
        delete(ModelElementIndex).where(
            ModelElementIndex.system_id == system_db_id
        )
    )

    for element in elements:
        db.add(
            ModelElementIndex(
                system_id=system_db_id,
                git_path=element["git_path"],
                layer=element["layer"],
                archimate_type=element["archimate_type"],
                name=element["name"],
                current_commit=element["current_commit"],
                updated_at=datetime.now(UTC),
            )
        )

    return len(elements)


@router.post("/github")
async def handle_github_webhook(
    request: Request,
    x_github_event: str | None = Header(
        default=None,
        alias="X-GitHub-Event",
    ),
    x_github_delivery: str | None = Header(
        default=None,
        alias="X-GitHub-Delivery",
    ),
    x_hub_signature_256: str | None = Header(
        default=None,
        alias="X-Hub-Signature-256",
    ),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    raw_body = await request.body()
    webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET")

    if not verify_github_signature(
        raw_body,
        x_hub_signature_256,
        webhook_secret,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing GitHub webhook signature.",
        )

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload.",
        ) from error

    expected_repository = os.getenv("GITHUB_MODEL_REPO")
    received_repository = payload.get("repository", {}).get("full_name")

    if received_repository != expected_repository:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Webhook repository does not match GITHUB_MODEL_REPO.",
        )

    if x_github_event != "pull_request":
        return {"status": "ignored", "reason": "Not a pull_request event."}

    action = payload.get("action")
    pull_request = payload.get("pull_request", {})

    if action != "closed" or pull_request.get("merged") is not True:
        return {
            "status": "ignored",
            "reason": "PR was not closed and merged.",
        }

    if not x_github_delivery:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-GitHub-Delivery header.",
        )

    pr_number = payload.get("number")
    if not isinstance(pr_number, int):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook payload is missing its top-level PR number.",
        )

    # Insert delivery first. The unique constraint makes redelivery a no-op.
    try:
        db.add(
            WebhookDelivery(
                delivery_id=x_github_delivery,
                event_type=x_github_event,
            )
        )
        db.flush()
    except IntegrityError:
        db.rollback()
        return {
            "status": "already_processed",
            "delivery_id": x_github_delivery,
        }

    artifact = db.execute(
        select(ArtifactVersion).where(
            ArtifactVersion.pr_number == pr_number
        )
    ).scalar_one_or_none()

    if artifact is None:
        db.commit()
        return {
            "status": "ignored",
            "reason": "No artifact version matches this PR number.",
            "pr_number": pr_number,
        }

    if artifact.approval_status == "approved":
        db.commit()
        return {
            "status": "already_approved",
            "pr_number": pr_number,
        }

    model_system_id = os.getenv("MODEL_SYSTEM_ID", "legacy-system")

    merge_commit_sha = pull_request.get("merge_commit_sha")
    if not merge_commit_sha:
        merge_commit_sha = pull_request.get("head", {}).get("sha")

    if not merge_commit_sha:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook payload has no merge commit SHA.",
        )

    try:
        indexed_count = rebuild_model_element_index(
            db=db,
            system_db_id=artifact.system_id,
            system_id=model_system_id,
            merge_commit_sha=merge_commit_sha,
        )

        artifact.approval_status = "approved"
        artifact.approved_by = (
            pull_request.get("merged_by", {}).get("login", "github_webhook")
        )
        artifact.approved_at = datetime.now(UTC)

        db.commit()

    except Exception:
        db.rollback()
        raise

    return {
        "status": "approved",
        "pr_number": pr_number,
        "indexed_elements": indexed_count,
        "commit_sha": merge_commit_sha,
    }
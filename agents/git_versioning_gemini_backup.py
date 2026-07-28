"""Git versioning and pull request automation for ArchiMate model repository (Epic G1 & G2)."""

from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session
from backend.repository.artifact_version_repository import create_artifact_version

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _get_configured_repo_dir(repo_dir: Path | None = None) -> Path:
    """Resolve and return the local git repository directory."""
    if repo_dir is not None:
        return Path(repo_dir).resolve()

    configured_path = os.environ.get("MODEL_REPO_DIR")
    if not configured_path:
        raise RuntimeError("MODEL_REPO_DIR is required in environment variables.")

    path = Path(configured_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def _sanitize_string(text: str, secret: str | None) -> str:
    """Mask secret token from error messages or logs."""
    if secret and secret in text:
        return text.replace(secret, "***SECRET_TOKEN***")
    return text


def _run_git_command(args: list[str], cwd: Path, token: str | None = None) -> str:
    """Execute a git subprocess command safely, catching and sanitizing errors."""
    env = os.environ.copy()
    if token:
        # Prevent git from prompting for passwords interactively
        env["GIT_TERMINAL_PROMPT"] = "0"

    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
            env=env,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raw_error = e.stderr or e.stdout or str(e)
        sanitized = _sanitize_string(raw_error, token)
        raise RuntimeError(f"Git command 'git {' '.join(args)}' failed: {sanitized}") from None


# ============================================================================
# G1: commit_to_model
# ============================================================================

def commit_to_model(
    system_id: str,
    run_id: str,
    commit_message: str | None = None,
    repo_dir: Path | None = None,
) -> dict[str, Any]:
    """
    G1: Commit working tree changes in MODEL_REPO_DIR to a feature branch and push to GitHub.

    Branch naming convention: feature/ingest-<system-id>-<run-id>
    Idempotent: If branch already exists and is pushed, handles gracefully.
    Security: Masks GITHUB_TOKEN in all logs/errors.
    """
    token = os.environ.get("GITHUB_TOKEN")
    model_repo = os.environ.get("GITHUB_MODEL_REPO")
    repo_path = _get_configured_repo_dir(repo_dir)

    if not (repo_path / ".git").exists():
        raise RuntimeError(f"Directory {repo_path} is not a valid git repository (no .git folder).")

    branch_name = f"feature/ingest-{system_id}-{run_id}"
    default_msg = f"feat(model): auto-extracted ArchiMate model [run_id: {run_id}]"
    msg = commit_message or default_msg

    # 1. Configure authenticated remote URL if token & repo are provided
    if token and model_repo:
        remote_url = f"https://x-access-token:{token}@github.com/{model_repo}.git"
        try:
            _run_git_command(["remote", "set-url", "origin", remote_url], cwd=repo_path, token=token)
        except Exception:
            _run_git_command(["remote", "add", "origin", remote_url], cwd=repo_path, token=token)

    # 2. Check if branch already exists
    local_branches = _run_git_command(["branch", "--list", branch_name], cwd=repo_path, token=token)
    branch_exists = bool(local_branches.strip())

    if branch_exists:
        _run_git_command(["checkout", branch_name], cwd=repo_path, token=token)
    else:
        _run_git_command(["checkout", "-b", branch_name], cwd=repo_path, token=token)

    # 3. Stage files under systems/<system_id>/as-is
    target_rel_path = f"systems/{system_id}/as-is"
    target_abs_path = repo_path / target_rel_path
    if target_abs_path.exists():
        _run_git_command(["add", target_rel_path], cwd=repo_path, token=token)

    # 4. Check status to see if anything is staged
    status_out = _run_git_command(["status", "--porcelain"], cwd=repo_path, token=token)
    if not status_out.strip():
        current_sha = _run_git_command(["rev-parse", "HEAD"], cwd=repo_path, token=token)
        return {
            "status": "no_changes",
            "branch": branch_name,
            "commit_sha": current_sha,
            "pushed": True,
            "message": "No new changes staged to commit.",
        }

    # 5. Commit
    _run_git_command(["commit", "-m", msg], cwd=repo_path, token=token)
    commit_sha = _run_git_command(["rev-parse", "HEAD"], cwd=repo_path, token=token)

    # 6. Push to remote
    pushed = False
    if token and model_repo:
        _run_git_command(["push", "-u", "origin", branch_name], cwd=repo_path, token=token)
        pushed = True

    return {
        "status": "success",
        "branch": branch_name,
        "commit_sha": commit_sha,
        "pushed": pushed,
        "message": f"Successfully committed and pushed branch {branch_name}",
    }


# ============================================================================
# G2: open_pull_request
# ============================================================================

def _generate_pr_body(system_id: str, run_id: str, repo_dir: Path) -> str:
    """Generate a rich GitHub PR description from F1 reconciler & F2 validator reports."""
    as_is_dir = repo_dir / "systems" / system_id / "as-is"
    reconciler_report_file = as_is_dir / "reconciliation-report.json"
    validator_report_file = as_is_dir / "validation-report.json"

    val_data = {}
    if validator_report_file.exists():
        try:
            val_data = json.loads(validator_report_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    rec_data = {}
    if reconciler_report_file.exists():
        try:
            rec_data = json.loads(reconciler_report_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    status = val_data.get("overall_status", "UNKNOWN")
    status_badge = "✅ **PASS**" if status == "PASS" else "❌ **FAIL**" if status == "FAIL" else "⚠️ **UNKNOWN**"

    body_lines = [
        f"# Automated Architecture Model Recovery — System: `{system_id}`",
        "",
        f"**Run ID**: `{run_id}`",
        f"**Validation Status**: {status_badge}",
        "",
        "## 📊 Model Summary",
        f"- **Total Elements**: {val_data.get('total_elements', 0)}",
        f"- **Total Relationships**: {val_data.get('total_relationships', 0)}",
        f"- **Validation Errors**: {val_data.get('error_count', 0)}",
        f"- **Validation Warnings**: {val_data.get('warning_count', 0)}",
        "",
        "### Layer Breakdown",
    ]

    coverage = val_data.get("coverage", [])
    if coverage:
        body_lines.append("| Layer | Elements | Relationships | Types Found |")
        body_lines.append("|-------|----------|---------------|-------------|")
        for layer in coverage:
            types_str = ", ".join(layer.get("element_types", [])) or "None"
            body_lines.append(
                f"| {layer.get('layer')} | {layer.get('element_count')} | "
                f"{layer.get('relationship_count')} | {types_str} |"
            )
        body_lines.append("")

    merges = rec_data.get("merges", [])
    conflicts = rec_data.get("conflicts", [])

    body_lines.extend([
        "## 🔄 Reconciliation Report (F1)",
        f"- **Elements Before**: {rec_data.get('total_elements_before', 'N/A')}",
        f"- **Elements After**: {rec_data.get('total_elements_after', 'N/A')}",
        f"- **Merged Duplicates**: {len(merges)}",
        f"- **Flagged Near-Miss Conflicts**: {len(conflicts)}",
        "",
    ])

    if conflicts:
        body_lines.append("### ⚠️ Flagged Near-Miss Conflicts for Review")
        body_lines.append("| Element A | Element B | Type | Similarity | Reason |")
        body_lines.append("|-----------|-----------|------|------------|--------|")
        for c in conflicts:
            body_lines.append(
                f"| `{c.get('element_a_name')}` | `{c.get('element_b_name')}` | "
                f"{c.get('archimate_type')} | {c.get('similarity_score')} | {c.get('reason')} |"
            )
        body_lines.append("")

    body_lines.extend([
        "---",
        "*Automated PR generated by Legacy System Agent pipeline.*",
    ])

    return "\n".join(body_lines)


def open_pull_request(
    system_id: str,
    run_id: str,
    db: Session | None = None,
    system_db_id: int = 1,
    commit_sha: str = "",
    repo_dir: Path | None = None,
) -> dict[str, Any]:
    """
    G2: Open GitHub Pull Request from feature branch against main, and record in DB.

    Idempotent: If PR already exists for branch, returns existing PR info.
    DB: Inserts artifact_versions record with approval_status="pending".
    """
    token = os.environ.get("GITHUB_TOKEN")
    model_repo = os.environ.get("GITHUB_MODEL_REPO")
    repo_path = _get_configured_repo_dir(repo_dir)

    if not token or not model_repo:
        raise RuntimeError("GITHUB_TOKEN and GITHUB_MODEL_REPO are required to open a PR.")

    branch_name = f"feature/ingest-{system_id}-{run_id}"
    pr_title = f"feat(model): recover ArchiMate model for {system_id} [run: {run_id}]"
    pr_body = _generate_pr_body(system_id, run_id, repo_path)

    # GitHub REST API call: POST /repos/{owner}/{repo}/pulls
    url = f"https://api.github.com/repos/{model_repo}/pulls"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Legacy-System-Agent",
    }
    data = {
        "title": pr_title,
        "head": branch_name,
        "base": "main",
        "body": pr_body,
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    pr_number = None
    pr_url = None

    try:
        with urllib.request.urlopen(req) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
            pr_number = resp_data.get("number")
            pr_url = resp_data.get("html_url")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        # Check if PR already exists (422 error from GitHub)
        if e.code == 422 and "A pull request already exists" in error_body:
            # Query existing PRs
            list_url = f"https://api.github.com/repos/{model_repo}/pulls?head={model_repo.split('/')[0]}:{branch_name}"
            list_req = urllib.request.Request(list_url, headers=headers)
            try:
                with urllib.request.urlopen(list_req) as list_resp:
                    existing_prs = json.loads(list_resp.read().decode("utf-8"))
                    if existing_prs:
                        pr_number = existing_prs[0].get("number")
                        pr_url = existing_prs[0].get("html_url")
            except Exception:
                pass
        else:
            sanitized_err = _sanitize_string(error_body, token)
            raise RuntimeError(f"GitHub API call failed ({e.code}): {sanitized_err}") from None

    # Record artifact version in database if db session provided
    artifact_record = None
    if db is not None:
        artifact_record = create_artifact_version(
            db=db,
            system_id=system_db_id,
            phase="as-is",
        )
        # Populate additional fields
        artifact_record.commit_sha = commit_sha
        artifact_record.tag = f"pr-{pr_number}" if pr_number else f"run-{run_id}"
        artifact_record.author_type = "agent"
        artifact_record.run_id = run_id
        artifact_record.approval_status = "pending"
        db.commit()
        db.refresh(artifact_record)

    return {
        "status": "success",
        "pr_number": pr_number,
        "pr_url": pr_url,
        "branch": branch_name,
        "commit_sha": commit_sha,
        "approval_status": "pending",
        "artifact_version_id": artifact_record.id if artifact_record else None,
    }

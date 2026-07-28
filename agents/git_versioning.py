"""Deterministic Git versioning for Epic G1."""

from __future__ import annotations

import base64
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


SAFE_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")


@dataclass(frozen=True)
class CommitResult:
    status: str
    branch: str
    commit_sha: str | None
    message: str


def validate_identifier(value: str, field_name: str) -> None:
    if not SAFE_IDENTIFIER.fullmatch(value):
        raise ValueError(
            f"{field_name} must contain only lowercase letters, digits, and hyphens."
        )


def model_repo_dir() -> Path:
    configured = os.getenv("MODEL_REPO_DIR")
    if not configured:
        raise RuntimeError("MODEL_REPO_DIR is not configured.")

    repo_dir = Path(configured).resolve()
    if not repo_dir.exists():
        raise RuntimeError(f"MODEL_REPO_DIR does not exist: {repo_dir}")

    return repo_dir


def git(
    args: list[str],
    *,
    cwd: Path,
    authenticated: bool = False,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run Git without placing GITHUB_TOKEN in a remote URL or command arguments."""
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"

    if authenticated:
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            raise RuntimeError("GITHUB_TOKEN is required for GitHub push.")

        encoded = base64.b64encode(
            f"x-access-token:{token}".encode("utf-8")
        ).decode("ascii")

        # Exists only for this subprocess; it is not written to .git/config.
        env["GIT_CONFIG_COUNT"] = "1"
        env["GIT_CONFIG_KEY_0"] = "http.https://github.com/.extraheader"
        env["GIT_CONFIG_VALUE_0"] = f"AUTHORIZATION: basic {encoded}"

    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    if check and result.returncode != 0:
        error = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"Git command failed: git {' '.join(args)}\n{error}")

    return result


def remote_branch_exists(repo_dir: Path, branch_name: str) -> bool:
    result = git(
        ["ls-remote", "--exit-code", "--heads", "origin", branch_name],
        cwd=repo_dir,
        authenticated=True,
        check=False,
    )
    return result.returncode == 0


def local_branch_exists(repo_dir: Path, branch_name: str) -> bool:
    result = git(
        ["show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"],
        cwd=repo_dir,
        check=False,
    )
    return result.returncode == 0


def commit_to_model(system_id: str, run_id: str) -> CommitResult:
    """
    G1:
    - Creates feature/ingest-<system-id>-<run-id>
    - Commits only systems/<system-id>/as-is
    - Pushes it to GitHub
    - Safely handles a retry using the same run_id
    """
    validate_identifier(system_id, "system_id")
    validate_identifier(run_id, "run_id")

    repo_dir = model_repo_dir()
    branch_name = f"feature/ingest-{system_id}-{run_id}"
    target_path = f"systems/{system_id}/as-is"

    is_git_repo = git(
        ["rev-parse", "--is-inside-work-tree"],
        cwd=repo_dir,
        check=False,
    )
    if is_git_repo.returncode != 0:
        raise RuntimeError(f"{repo_dir} is not a Git repository.")

    if not (repo_dir / target_path).exists():
        raise RuntimeError(f"Model output folder does not exist: {target_path}")

    # Refresh main and check GitHub first, not only local branches.
    git(["fetch", "origin", "main"], cwd=repo_dir, authenticated=True)

    if remote_branch_exists(repo_dir, branch_name):
        sha = git(
            ["rev-parse", f"origin/{branch_name}"],
            cwd=repo_dir,
            authenticated=True,
        ).stdout.strip()

        return CommitResult(
            status="already_pushed",
            branch=branch_name,
            commit_sha=sha,
            message="This run already has a branch on GitHub; no new commit was created.",
        )

    # Recover safely if a previous attempt created the branch locally before push.
    if local_branch_exists(repo_dir, branch_name):
        git(["switch", branch_name], cwd=repo_dir)

        staged = git(
            ["diff", "--cached", "--name-only"],
            cwd=repo_dir,
        ).stdout.strip()

        if staged:
            git(
                [
                    "commit",
                    "-m",
                    f"feat(model): ingest {system_id} [run_id: {run_id}]",
                ],
                cwd=repo_dir,
            )

        sha = git(["rev-parse", "HEAD"], cwd=repo_dir).stdout.strip()
        git(["push", "-u", "origin", branch_name], cwd=repo_dir, authenticated=True)

        git(["switch", "main"], cwd=repo_dir, check=False)

        return CommitResult(
            status="recovered_and_pushed",
            branch=branch_name,
            commit_sha=sha,
            message="Recovered the local branch and pushed it to GitHub.",
        )

    # The pipeline writes model files before G1 runs, so creating the branch
    # must preserve those uncommitted files.
    current_branch = git(
        ["branch", "--show-current"],
        cwd=repo_dir,
    ).stdout.strip()

    if current_branch != "main":
        raise RuntimeError(
            "G1 must start from the local main branch. "
            f"Current branch is: {current_branch}"
        )

    local_main_sha = git(
        ["rev-parse", "HEAD"],
        cwd=repo_dir,
    ).stdout.strip()

    remote_main_sha = git(
        ["rev-parse", "origin/main"],
        cwd=repo_dir,
    ).stdout.strip()

    if local_main_sha != remote_main_sha:
        raise RuntimeError(
            "Local main is not equal to origin/main. "
            "Update main before the pipeline generates model files."
        )

    try:
        # `switch -c` without origin/main preserves the model files that E/F created.
        git(["switch", "-c", branch_name], cwd=repo_dir)

        # Stage only model output for this system.
        git(["add", "--", target_path], cwd=repo_dir)

        staged_files = git(
            ["diff", "--cached", "--name-only"],
            cwd=repo_dir,
        ).stdout.strip().splitlines()

        if not staged_files:
            return CommitResult(
                status="no_changes",
                branch=branch_name,
                commit_sha=None,
                message="No model files changed, so no commit was created.",
            )

        # Safety check: do not accidentally commit unrelated files.
        for file_name in staged_files:
            if not file_name.startswith(f"{target_path}/"):
                raise RuntimeError(
                    f"Refusing to commit unrelated staged file: {file_name}"
                )

        git(
            [
                "commit",
                "-m",
                f"feat(model): ingest {system_id} [run_id: {run_id}]",
            ],
            cwd=repo_dir,
        )

        commit_sha = git(["rev-parse", "HEAD"], cwd=repo_dir).stdout.strip()
        git(["push", "-u", "origin", branch_name], cwd=repo_dir, authenticated=True)

        return CommitResult(
            status="pushed",
            branch=branch_name,
            commit_sha=commit_sha, 
            message="Feature branch was created, committed, and pushed.",
        )

    finally:
        git(["switch", "main"], cwd=repo_dir, check=False)
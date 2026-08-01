"""H1: deterministic sequencing around the evidence-ingestion agents."""

from __future__ import annotations

import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from agents.base_agent import create_base_agent
from agents.git_versioning import commit_to_model
from agents.pull_requests import open_pull_request
from agents.reconciler import run_reconciler
from agents.validator import ValidationReport, run_validator
from backend.database.models.legacy_system import LegacySystem
from backend.database.session import SessionLocal
from backend.llms.gemini import get_llm as get_fallback_llm
from backend.repository.legacy_system_repository import get_legacy_system_by_name


class PipelineError(RuntimeError):
    """A pipeline stage failed and subsequent stages must not run."""


class PipelineValidationError(PipelineError):
    """The validator rejected the model, so Git operations are forbidden."""


@dataclass(frozen=True)
class IngestionResult:
    run_id: str
    system_id: str
    pr_number: int
    pr_url: str
    commit_sha: str


PARALLEL_ANALYSTS = (
    "strategy-analyst",
    "business-analyst",
    "code-analyzer",
    "infra-analyzer",
)
DEFAULT_ANALYST_CONCURRENCY = 1


def _analyst_concurrency() -> int:
    """Keep hosted-model calls within the provider's concurrent-request limit."""
    configured = int(
        os.getenv("INGESTION_ANALYST_CONCURRENCY", DEFAULT_ANALYST_CONCURRENCY)
    )
    if not 1 <= configured <= len(PARALLEL_ANALYSTS):
        raise PipelineError(
            "INGESTION_ANALYST_CONCURRENCY must be between 1 and "
            f"{len(PARALLEL_ANALYSTS)}."
        )
    return configured


def _configured_path(variable_name: str) -> Path:
    value = os.getenv(variable_name)
    if not value:
        raise PipelineError(f"{variable_name} must be configured.")
    return Path(value).resolve()


def _validate_pipeline_scope(system_id: str, evidence_path: str | Path) -> None:
    configured_system = os.getenv("MODEL_SYSTEM_ID", "legacy-system")
    if system_id != configured_system:
        raise PipelineError(
            "This single-system MVP accepts only MODEL_SYSTEM_ID "
            f"({configured_system!r}), not {system_id!r}."
        )

    configured_evidence = _configured_path("EVIDENCE_DIR")
    requested_evidence = Path(evidence_path).resolve()
    if requested_evidence != configured_evidence:
        raise PipelineError(
            "evidence_path must match the configured EVIDENCE_DIR for this MVP."
        )


def _invoke_subagent(subagent_name: str, run_id: str) -> None:
    """Use the Deep Agent task tool and attach the run ID to LangSmith metadata."""
    prompt = (
        f"Run ID: {run_id}. Use the task tool to delegate exactly once to "
        f"the {subagent_name} subagent. It must analyze its assigned evidence "
        "and write only validated output. Report the returned result."
    )
    config = {
        "run_name": f"as-is-{subagent_name}",
        "metadata": {"run_id": run_id},
    }

    try:
        create_base_agent().invoke(
            {"messages": [("user", prompt)]},
            config=config,
        )
    except Exception as error:  # noqa: BLE001 - provider errors are SDK-specific
        error_text = str(error).lower()
        is_provider_outage = (
            "internalservererror" in error_text
            or "rate limit" in error_text
            or "rate_limit" in error_text
            or "error code: 500" in error_text
            or "error code: 429" in error_text
        )
        if not is_provider_outage:
            raise

        # Continue the same analysis with an independent provider when the
        # hosted Ollama/OpenAI-compatible endpoint is temporarily unavailable.
        create_base_agent(model=get_fallback_llm()).invoke(
            {"messages": [("user", prompt)]},
            config=config,
        )


def _run_parallel_analysts(run_id: str) -> None:
    with ThreadPoolExecutor(max_workers=_analyst_concurrency()) as executor:
        futures = [
            executor.submit(_invoke_subagent, analyst, run_id)
            for analyst in PARALLEL_ANALYSTS
        ]
        for future in futures:
            future.result()


def run_as_is_ingestion(
    system_id: str,
    evidence_path: str | Path,
    *,
    run_id: str | None = None,
    db: Session | None = None,
    system_db_id: int | None = None,
) -> IngestionResult:
    """Run E1-E5, F1-F2, G1 and G2 in the required order.

    Any exception stops the pipeline. In particular, a failing validator never
    reaches the Git commit or PR stages.
    """
    _validate_pipeline_scope(system_id, evidence_path)
    run_id = run_id or str(uuid.uuid4())
    owns_session = db is None
    db = db or SessionLocal()

    try:
        system = (
            db.get(LegacySystem, system_db_id)
            if system_db_id is not None
            else get_legacy_system_by_name(db, system_id)
        )
        if system is None:
            raise PipelineError(f"No legacy system exists for {system_id!r}.")
        if system.name != system_id:
            raise PipelineError("Job system ID does not match MODEL_SYSTEM_ID.")

        _run_parallel_analysts(run_id)
        _invoke_subagent("integration-mapper", run_id)

        run_reconciler()
        report: ValidationReport = run_validator()
        if report.overall_status != "PASS":
            raise PipelineValidationError(
                f"Validation failed with {report.error_count} error(s); G1/G2 were not run."
            )

        commit = commit_to_model(system_id, run_id)
        if commit.commit_sha is None:
            raise PipelineError("G1 produced no commit; G2 will not open an empty PR.")

        pull_request = open_pull_request(
            db=db,
            system_db_id=system.id,
            system_id=system_id,
            run_id=run_id,
            commit_sha=commit.commit_sha,
        )
        return IngestionResult(
            run_id=run_id,
            system_id=system_id,
            pr_number=pull_request["pr_number"],
            pr_url=pull_request["pr_url"],
            commit_sha=commit.commit_sha,
        )
    finally:
        if owns_session:
            db.close()            

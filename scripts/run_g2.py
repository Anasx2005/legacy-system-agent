import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import select

load_dotenv()

from agents.pull_requests import open_pull_request
from backend.database.models.legacy_system import LegacySystem
from backend.database.session import SessionLocal


SYSTEM_ID = "legacy-system"
RUN_ID = "run-002"
BRANCH_NAME = f"feature/ingest-{SYSTEM_ID}-{RUN_ID}"

repo_dir = Path(os.environ["MODEL_REPO_DIR"]).resolve()

commit_sha = subprocess.check_output(
    ["git", "rev-parse", f"origin/{BRANCH_NAME}"],
    cwd=repo_dir,
    text=True,
).strip()

db = SessionLocal()

try:
    system = db.execute(
        select(LegacySystem).where(
            LegacySystem.name == SYSTEM_ID
        )
    ).scalar_one_or_none()

    if system is None:
        raise RuntimeError(
            "No legacy_systems row exists for legacy-system. "
            "B1/B2 data setup is required before G2."
        )

    result = open_pull_request(
        db=db,
        system_db_id=system.id,
        system_id=SYSTEM_ID,
        run_id=RUN_ID,
        commit_sha=commit_sha,
    )

    print(result)

finally:
    db.close()
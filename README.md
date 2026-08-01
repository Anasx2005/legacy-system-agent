# Legacy System Agent

The MVP turns evidence about one legacy system into reviewed ArchiMate model
JSON. The five ingestion subagents write evidence-cited elements, reconciliation
deduplicates them, validation gates GitHub PR creation, and a GitHub merge
webhook publishes the approved version to the viewer.

## Requirements

- Python 3.11+, [uv](https://docs.astral.sh/uv/), Git, Docker Desktop, and Node.js 20+.
- A GitHub repository for generated model files, with a local checkout at `MODEL_REPO_DIR`.
- An Ollama API key for the currently configured `gpt-oss:20b-cloud` model.

## Fresh checkout

```powershell
git clone https://github.com/Anasx2005/legacy-system-agent.git
cd legacy-system-agent
uv sync
Copy-Item .env.example .env
docker compose up -d
uv run alembic upgrade head
uv run python scripts/ensure_legacy_system.py
```

Edit `.env` before starting the application:

| Variable | Value and where to obtain it |
| --- | --- |
| `DATABASE_URL` | Use the local Docker default from `.env.example`, unless your PostgreSQL differs. |
| `OLLAMA_API_KEY` | Create an API key at [Ollama settings](https://ollama.com/settings/keys). This is required by the current configured model. |
| `GITHUB_TOKEN` | Create a fine-grained, repository-scoped PAT in GitHub with contents and pull-request write permission. |
| `GITHUB_MODEL_REPO` | `owner/repository` of the generated-model repository. |
| `MODEL_REPO_DIR` | Local checkout of that same repository; it must contain `systems/legacy-system/`. |
| `GITHUB_WEBHOOK_SECRET` | Generate a random secret and enter the identical value in the GitHub webhook configuration. |
| `API_KEY` | Generate a long random local API key used by the backend and browser UI. |
| `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT`, `LANGCHAIN_TRACING_V2` | Create a key at [LangSmith](https://smith.langchain.com/) and set tracing to `true`; use a project such as `legacy-system-agent`. |

`ANTHROPIC_API_KEY` is not required by the checked-in runtime: it currently uses
Ollama. If you later change the LLM adapter to Anthropic, create its key in the
[Anthropic Console](https://console.anthropic.com/) and add the corresponding
adapter configuration; do not replace `OLLAMA_API_KEY` without that code change.

## Run locally

Start the backend in one terminal:

```powershell
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Start the viewer in a second terminal:

```powershell
cd frontend
Copy-Item .env.example .env
npm install
npm run dev
```

Set `VITE_API_BASE_URL=http://127.0.0.1:8000`. Leave `VITE_API_KEY` blank and
enter the value in the browser when prompted; it stays only in the browser
session. Set `VITE_GITHUB_MODEL_REPO`, `VITE_EVIDENCE_GITHUB_REPO`, and
`VITE_EVIDENCE_GITHUB_REF` to make PR and evidence links clickable.

## Epic J acceptance flow

The stable fictional evidence fixture is in [`test-fixtures/`](test-fixtures/README.md).
For the acceptance run, set `EVIDENCE_DIR=test-fixtures/evidence` and restart
the backend. In the viewer's **Run** page, enter that exact server-side path
and choose **Run ingestion**. Do not use a script to trigger this step.

1. For the negative gate check, allow the integration mapper to propose the
   relationship in `customer-api-invalid.yaml`. The job must fail before any
   Git commit or PR; its validation report must identify
   `app-retired-billing-service` as a missing relationship target.
2. Remove that proposed relationship (the mapper should normally skip it) and
   run again from a clean model-output branch/database. Confirm all five
   subagents run, the `Customer API`/`customer-api` duplicate becomes one
   element with both citations, and the job opens a readable GitHub PR.
3. Inspect the PR in GitHub and merge it using the normal GitHub UI. This is a
   human approval gate; do not mark the artifact approved in the database.
4. Expose `POST /webhooks/github` over HTTPS and configure a GitHub **Pull
   requests** webhook with `GITHUB_WEBHOOK_SECRET`. After the merge, confirm
   the webhook marks the artifact version `approved` and rebuilds its element
   index from `origin/main`.
5. In the viewer, confirm the elements are grouped by layer and their evidence
   links work. On **Versions**, confirm the approved version links to the PR.
   In LangSmith, search for the run ID from the Run page and confirm the
   connected subagent trace.

Run this flow twice from clean state. Structural results must agree; only LLM
wording may vary. The local deterministic checks are:

```powershell
uv run pytest tests/test_epic_j_acceptance.py
```

## API

All Phase 1 endpoints require `X-API-Key`. Interactive docs are at
`http://127.0.0.1:8000/docs`.

| Endpoint | Purpose |
| --- | --- |
| `POST /systems/{system_id}/ingest` | Queue ingestion with `{ "evidence_path": "..." }`. |
| `GET /jobs/{job_id}` | Return job status and its LangSmith correlation ID. |
| `GET /systems/{system_id}/elements` | List approved, indexed model elements. |
| `GET /elements/{element_id}` | Read model detail and evidence from `main`. |
| `GET /systems/{system_id}/artifact-versions` | List PR-backed artifact versions and approval state. |

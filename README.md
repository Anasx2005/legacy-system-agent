# Legacy System Agent

## Requirements

- Python 3.11+
- Docker Desktop
- Git
- uv


## Setup

Clone the repository

```bash
git clone <https://github.com/Anasx2005/legacy-system-agent.git>
```

Go to the project directory

```bash
cd Legacy-System-Agent
```


Synchronize dependencies

```bash
uv sync
```


Run PostgreSQL using Docker

```bash
docker compose up -d
```


Check the running container

```bash
docker compose ps
```


## Environment Variables

Create a .env file and add the following variables:


```text
DATABASE_URL=

GITHUB_TOKEN=

GITHUB_MODEL_REPO=

LANGCHAIN_API_KEY=

LANGCHAIN_PROJECT=

LANGCHAIN_TRACING_V2=
```

## GitHub PR-merge webhook (G3)

Expose `POST /webhooks/github` over HTTPS, then configure a GitHub repository webhook for
the **Pull requests** event. Set the same random value in GitHub's webhook secret field and
in `GITHUB_WEBHOOK_SECRET`. The endpoint verifies GitHub's `X-Hub-Signature-256` before it
accepts a merge event; it then marks the matching artifact version as approved and rebuilds
the model-element index from `origin/main`.

## Phase 1 orchestration API (Epic H)

Set `API_KEY` to a long random value and pass it in the `X-API-Key` header for every
Phase 1 endpoint. Start the API with:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Interactive OpenAPI documentation is available at `http://127.0.0.1:8000/docs`.

| Endpoint | Purpose |
| --- | --- |
| `POST /systems/{system_id}/ingest` | Queue a Phase 1 run with `{ "evidence_path": "..." }`. |
| `GET /jobs/{job_id}` | Get queued/running/succeeded/failed status and its trace correlation ID. |
| `GET /systems/{system_id}/elements?layer=application` | List approved indexed elements. |
| `GET /elements/{element_id}` | Read element detail and evidence from the model repository's `main` branch. |
| `GET /systems/{system_id}/artifact-versions` | List PRs and their approval status. |

For this single-system MVP, the evidence path supplied to `POST /ingest` must be exactly
the configured `EVIDENCE_DIR`, and the database system name must match `MODEL_SYSTEM_ID`.


## Database

Default PostgreSQL configuration:

```text
User:
app_user


Database:
legacy_db


Port:
5432
```


Check PostgreSQL container:

```bash
docker ps
```


Stop PostgreSQL:

```bash
docker compose down
```


Start PostgreSQL:

```bash
docker compose up -d
```

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

# StoryDiff backend

Python package: **`storydiff`**. Use [uv](https://docs.astral.sh/uv/) to manage the environment and dependencies.

## Setup

From `backend/`:

1. Create the virtual environment (once per machine / when you want a fresh env):

```bash
uv venv
```

2. Install dependencies and this package in editable mode:

```bash
uv sync --group dev
```

`uv sync` uses `.venv` in this directory; creating it with `uv venv` first makes the two steps explicit. If `.venv` is missing, `uv sync` will create it anyway.

Activate when you want `python` / `alembic` on your PATH without the `uv run` prefix:

```bash
source .venv/bin/activate   # Linux / macOS
# .venv\Scripts\activate    # Windows
```

Run tools without activating the venv:

```bash
uv run alembic upgrade head
uv run python -c "from storydiff.db import Base; print(Base.metadata.tables.keys())"
```

Or activate `.venv` and use `alembic` / `python` normally.

## Imports

- **ORM models:** `from storydiff.db import Base` and model classes (`MediaOutlet`, `Article`, …) exported from `storydiff.db`.
- **Qdrant:** `storydiff.qdrant` — settings, payload field names, `ensure_collections()`.

## Environment

Copy `.env.example` to `.env` in `backend/` and set values (never commit secrets). `DATABASE_URL` uses the SQLAlchemy URL form for psycopg v3, e.g. `postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME`.

**Alembic** loads `backend/.env` automatically via `python-dotenv`, so `uv run alembic …` picks up `DATABASE_URL` without `export`. Variables already set in your shell still win over `.env`.

## Docker Compose (local Postgres + Qdrant)

From the **repository root** (where `docker-compose.yml` lives):

```bash
docker compose up -d
```

This starts:

- **Postgres** — `localhost:5432` (user/password/db match `backend/.env.example`)
- **Qdrant** — REST and dashboard on `http://localhost:6333`, gRPC on `6334`

Data persists in named volumes (`storydiff_pgdata`, `storydiff_qdrant`). Stop with `docker compose down`; remove volumes with `docker compose down -v` (wipes DB and vector store).

## Postgres (dev)

1. Run PostgreSQL 15+ locally, or use Docker Compose above and create an empty database (Compose already creates `storydiff`).
2. From `backend/`, with `DATABASE_URL` in `.env` (or exported):

```bash
uv venv
uv sync --group dev
uv run alembic upgrade head
```

Rollback to empty (before Phase 1 tables):

```bash
uv run alembic downgrade base
```

`base` is the state with no StoryDiff tables from this migration chain.

## Qdrant (dev)

Set `QDRANT_URL` (and optional `QDRANT_API_KEY`) in `backend/.env`. `load_qdrant_settings()` loads that file (same as Alembic). Vector size and distance **must** match the embedding model used for articles and topics.

```bash
uv run python -c "from storydiff.qdrant.collections import ensure_collections; ensure_collections()"
```

Point IDs: use Postgres `article_id` / `topic_id` as Qdrant point IDs for idempotent upserts (see `storydiff/qdrant/collections.py`).

## Lockfile

After changing dependencies in `pyproject.toml`, refresh the lockfile:

```bash
uv lock
```

Commit `uv.lock` with the project so installs are reproducible.

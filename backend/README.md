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
- **HTTP API:** `storydiff.main:app` — FastAPI app with `POST /api/v1/ingest` and Core Read `GET` routes under `/api/v1` (feed, topics, media, search, categories).

## Environment

Copy `.env.example` to `.env` in `backend/` and set values (never commit secrets). `DATABASE_URL` uses the SQLAlchemy URL form for psycopg v3, e.g. `postgresql+psycopg://USER:PASSWORD@HOST:PORT/DBNAME`.

**Alembic** loads `backend/.env` automatically via `python-dotenv`, so `uv run alembic …` picks up `DATABASE_URL` without `export`. Variables already set in your shell still win over `.env`.

### Ingestion / SQS

Ingestion publishes `article.ingested` and (when not a duplicate) `article.analyze` to the queues named in `SQS_ARTICLE_INGESTED_QUEUE_URL` and `SQS_ARTICLE_ANALYZE_QUEUE_URL`. Set `AWS_ENDPOINT_URL` to point boto3 at [LocalStack](https://docs.localstack.cloud/) (e.g. `http://localhost:4566`) in local dev. Dummy credentials (`AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`) are fine for LocalStack.

## Docker Compose (local Postgres + Qdrant + LocalStack)

From the **repository root** (where `docker-compose.yml` lives):

```bash
docker compose up -d
```

This starts:

- **Postgres** — host port **`5434`** → container `5432` (user/password/db match `backend/.env.example` when using that port)
- **Qdrant** — REST and dashboard on `http://localhost:6333`, gRPC on `6334`
- **LocalStack** — SQS on **`http://localhost:4566`**

Create the ingestion queues once (requires [AWS CLI](https://aws.amazon.com/cli/)):

```bash
chmod +x scripts/localstack-init-sqs.sh   # once
./scripts/localstack-init-sqs.sh
```

Paste the printed queue URLs into `backend/.env` as `SQS_ARTICLE_INGESTED_QUEUE_URL` and `SQS_ARTICLE_ANALYZE_QUEUE_URL`.

Data persists in named volumes (`storydiff_pgdata`, `storydiff_qdrant`, `storydiff_localstack`). Stop with `docker compose down`; remove volumes with `docker compose down -v` (wipes DB, vector store, and LocalStack state).

### Article analysis worker (Phase 2–3)

The worker consumes `article.analyze` from `SQS_ARTICLE_ANALYZE_QUEUE_URL`, runs a LangGraph pipeline (embed → Qdrant → classify → entities → summary/scores → **topic assignment** → Qdrant → Postgres), and refreshes the article point in Qdrant. Topic assignment scores candidates from `topic_embeddings`, links the article or creates a topic, writes `topic_article_links` (including `consensus_distance` when a topic vector exists), and publishes `topic.refresh` to `SQS_TOPIC_REFRESH_QUEUE_URL` when that queue is configured. Set `EMBEDDING_VECTOR_SIZE=384` and (re)create the `article_embeddings` and `topic_embeddings` collections if you previously used a different dimension.

- **LLM:** default `LLM_PROVIDER=ollama` with `OLLAMA_MODEL=llama3.1:8b` (OpenAI-compatible API at `OLLAMA_BASE_URL`). Switch to OpenAI with `LLM_PROVIDER=openai` and `OPENAI_API_KEY`.
- **Embeddings:** default `EMBEDDING_BACKEND=ollama` uses Ollama `POST /api/embeddings` with `OLLAMA_EMBEDDING_MODEL=all-minilm` (384-d). Optional: `uv sync --extra embeddings-st` and `EMBEDDING_BACKEND=sentence_transformers` for Hugging Face `all-MiniLM-L6-v2`.

Run after [Ollama](https://ollama.com/) is up and models are pulled (`ollama pull llama3.1:8b`, `ollama pull all-minilm`):

```bash
cd backend && uv run python -m storydiff.analysis
```

### Topic refresh worker (Phase 3)

Consumes `topic.refresh` from `SQS_TOPIC_REFRESH_QUEUE_URL`, locks the topic row, skips if within `TOPIC_REFRESH_COOLDOWN_SECONDS`, loads linked articles in `TOPIC_REFRESH_WINDOW_HOURS`, recomputes consensus (LLM) and `topic_versions`, upserts the topic vector in Qdrant, and backfills `consensus_distance` on `topic_article_links`.

```bash
cd backend && uv run python -m storydiff.topic_refresh
```

**LangGraph checkpointing:** by default (`LANGGRAPH_CHECKPOINT_ENABLED=true`) the analysis graph uses a **Postgres** checkpointer (`langgraph-checkpoint-postgres`) with `thread_id` = `article-analysis-<article_id>`. Tables (`checkpoints`, `checkpoint_blobs`, …) are created on first run via `PostgresSaver.setup()` (same Postgres as `DATABASE_URL`, or set `CHECKPOINT_DATABASE_URL`). Disable with `LANGGRAPH_CHECKPOINT_ENABLED=false` for local experiments without checkpoint tables.

## HTTP API (dev)

With migrations applied and `DATABASE_URL` set:

```bash
uv run uvicorn storydiff.main:app --reload --host 127.0.0.1 --port 8000
```

- Health: `GET http://127.0.0.1:8000/health`
- Ingest: `POST http://127.0.0.1:8000/api/v1/ingest` (JSON body per `architecture/api_contract.md` §8.1)
- Core read (envelope `data` / `meta` / `error` per §Common Response Envelope):
  - `GET /api/v1/categories`
  - `GET /api/v1/feed` — optional query params: `category`, `limit_per_category`, `include_empty_categories`
  - `GET /api/v1/topics/{topicId}` — `include_articles`, `include_timeline_preview`
  - `GET /api/v1/topics/{topicId}/timeline`
  - `GET /api/v1/media` — `window`, `category`, `limit`, `sort_by`
  - `GET /api/v1/media/{mediaId}`
  - `GET /api/v1/search` — required `q`; optional `mode` (`keyword` \| `semantic` \| `hybrid`), `type` (`topics` \| `articles` \| `all`), `category`, `from`, `to`, `limit`. Keyword mode uses Postgres only; semantic/hybrid need `QDRANT_URL` and `EMBEDDING_VECTOR_SIZE` (and a working embedding backend).

## Tests

```bash
uv run pytest
```

Pure unit tests (dedupe helpers, moto SQS) run without Postgres. **`tests/ingest_api/`** exercises `POST /api/v1/ingest` against PostgreSQL and is **skipped** if the DB is unreachable. **`tests/core_api/`** covers Core Read GET routes; it requires a **migrated** database (same `TEST_DATABASE_URL` / `alembic upgrade head` as your app schema). Point tests at Compose Postgres with:

```bash
export TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5434/storydiff
uv run pytest
```

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

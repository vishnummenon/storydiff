# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**StoryDiff** is a multi-source narrative variance analyzer. It ingests news articles, clusters them into topics using AI, computes narrative variance metrics (consensus distance, framing polarity, source diversity, etc.), and exposes read-optimized APIs consumed by a Next.js frontend.

## Commands

### Backend (`backend/` directory)

```bash
# Setup
uv venv && uv sync --group dev

# Run API server
uv run uvicorn storydiff.main:app --reload --host 127.0.0.1 --port 8000

# Run workers
uv run python -m storydiff.analysis        # Article analysis worker (SQS consumer)
uv run python -m storydiff.topic_refresh   # Topic refresh worker (SQS consumer)

# Database migrations
uv run alembic upgrade head
uv run alembic downgrade base

# Tests (point TEST_DATABASE_URL at Docker Compose Postgres on port 5434)
export TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5434/storydiff
uv run pytest                  # All tests
uv run pytest tests/path/to/test_file.py  # Single test file
```

### Frontend (`web/` directory)

```bash
npm install
npm run dev       # Dev server at http://localhost:3000 (Turbopack)
npm run build && npm start
npm run lint
```

### Local Infrastructure (repo root)

```bash
docker compose up -d                        # Postgres (5434), Qdrant (6333/6334), LocalStack (4566)
./scripts/localstack-init-sqs.sh            # Create SQS queues (requires AWS CLI)
```

## Architecture

### Data Flow

```
POST /api/v1/ingest
  → Ingestion Service: validate, dedupe, upsert article → Postgres
  → Publish article.analyze to SQS
    → Analysis Worker (LangGraph): embed → classify category → extract entities
      → assign/create topic → summarize → score → persist to Postgres + Qdrant
      → Publish topic.refresh to SQS
        → Topic Refresh Worker (LangGraph): recompute consensus title/summary
          → version snapshot → update topic embedding in Qdrant

Read APIs (GET /api/v1/*) serve from Postgres
Next.js frontend SSR fetches from FastAPI directly (server-side) or via rewrites (browser)
```

### Storage Responsibilities

- **Postgres**: Source of truth for all records and analysis outputs
- **Qdrant**: Semantic retrieval only — `article_embeddings` (for search & topic candidate lookup) and `topic_embeddings` (for topic assignment matching). Point IDs match Postgres IDs.
- **SQS**: Async event queue decoupling ingest from AI work

### Key Backend Modules

| Module | Role |
|--------|------|
| `storydiff/ingestion/` | POST /ingest handler — dedupe, upsert, publish to SQS |
| `storydiff/analysis/graph.py` | LangGraph state machine for article analysis |
| `storydiff/analysis/topic_assignment.py` | Topic matching & creation logic |
| `storydiff/topic_refresh/` | LangGraph workflow for topic consensus recomputation |
| `storydiff/core_api/` | Read endpoints (feed, topics, media, search) |
| `storydiff/db/models.py` | SQLAlchemy models |
| `storydiff/qdrant/` | Qdrant collection setup and payload definitions |

### Deduplication Priority

Article deduplication checks in order: canonical URL hash → source article ID → fingerprint (normalized title + outlet + publish-date bucket).

### Scores

- **Consensus distance**: How much an article diverges from its topic cluster
- **Framing polarity**: Tone/intensity of framing
- **Source diversity**: Breadth of perspectives in topic
- **Novel claim**: How cluster-distinctive the article's content is
- **Reliability**: System confidence (not truthfulness)

### Frontend

Next.js 15 App Router with SSR. Server-side fetches use `API_BASE_URL` (env var, default `http://127.0.0.1:8000`). Browser requests rewrite `/api/v1/*` to the backend via `next.config.ts` (no CORS needed). All pages use `force-dynamic` in v1.

## Environment

Copy `backend/.env.example` → `backend/.env` and `web/.env.example` → `web/.env.local`. Key backend vars: `DATABASE_URL`, `QDRANT_URL`, `SQS_*`, `LLM_PROVIDER`, `OLLAMA_*`.

## Architecture Documentation

Detailed specs live in `architecture/`:
- `hld.md` — Full high-level design, component responsibilities, build phases
- `db_schema.md` — Table definitions and index recommendations
- `api_contract.md` — Complete API spec with request/response examples
- `score_semantics.md` — Score interpretation guide
- `events.md` — SQS event payload definitions

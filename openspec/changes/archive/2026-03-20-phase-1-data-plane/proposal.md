## Why

StoryDiff needs a durable Phase 1 data plane before ingest, workers, and APIs: Postgres as the relational source of truth for prototype v1 entities and Qdrant for article/topic embeddings. Without this foundation, later phases cannot persist or retrieve data consistently. Aligning now with [architecture/build_order.md](../../../architecture/build_order.md) (Phase 1), [architecture/db_schema.md](../../../architecture/db_schema.md), and [architecture/implementation_choices.md](../../../architecture/implementation_choices.md) avoids rework when `/ingest` and analysis pipelines land.

## What Changes

- Introduce the full prototype v1 relational model in Postgres: `media_outlets`, `categories`, `articles`, `article_analysis`, `article_entities`, `topics`, `topic_versions`, `topic_article_links`, `media_aggregates`, and `api_request_logs` (included in scope), matching SQL semantics in `db_schema.md` (including `dedupe_key` uniqueness, enum-like `processing_status` strings, 1:1 `article_analysis`↔`articles`, JSONB where specified, FKs and `ON DELETE CASCADE` as documented, and **no** FK from `articles.topic_id` to `topics` unless product explicitly changes that).
- Apply all indexes from §4 of `db_schema.md`.
- Add Alembic-managed initial migration(s) that create the above from an empty database; document dev `upgrade` / `downgrade` and environment-based database URL with no secrets committed.
- Add SQLAlchemy models (or Core table definitions) in a single importable Python package consistent with the migrated schema.
- Define Qdrant collections `article_embeddings` and `topic_embeddings` per §5, with payload field names and types matching §5.1 and §5.2 examples; expose vector size and distance metric as explicit configuration (documented as must match the embedding model used for articles and topics).
- Document point-ID strategy (e.g. use `article_id` / `topic_id` as the Qdrant point id for idempotent upserts) in `design.md`.

**Explicitly out of scope:** `/ingest` HTTP API, dedupe/upsert business logic, queues, workers, embedding generation, LangGraph, Next.js, read APIs.

## Capabilities

### New Capabilities

- `postgres-relations`: Relational source of truth—tables, constraints, indexes, Alembic migrations, and SQLAlchemy definitions per `db_schema.md` §3–4 and implementation choices (SQLAlchemy + Alembic).
- `qdrant-embeddings`: Vector collections, payload contracts, configuration for vector size and distance, and point-ID strategy per `db_schema.md` §5.

### Modified Capabilities

- *(None—no existing specs under `openspec/specs/`.)*

## Impact

- **Code:** New Python backend package(s) for DB models and Alembic env; optional thin Qdrant bootstrap or config module using `qdrant-client` (or equivalent official client).
- **Dependencies:** SQLAlchemy, Alembic, `psycopg` (or agreed Postgres driver), `qdrant-client` (or equivalent).
- **Infrastructure:** Postgres and Qdrant instances for local/dev; connection settings via environment variables only.
- **APIs / product:** No user-facing API changes in this change; prepares persistence for later ingest and read paths.

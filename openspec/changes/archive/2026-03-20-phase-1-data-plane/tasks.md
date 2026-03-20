## 1. Project and dependencies

- [ ] 1.1 Add or extend Python project metadata for SQLAlchemy, Alembic, Postgres driver (`psycopg` or project standard), and `qdrant-client` (no alternate ORM or migration stack).
- [ ] 1.2 Choose the single import path for persistence models (package/module layout) and document it in code layout only as needed for consistency.

## 2. Alembic and environment

- [ ] 2.1 Initialize Alembic (if not present) with `env.py` reading database URL from environment (e.g. `DATABASE_URL`); add `.env.example` with placeholder only—no secrets in repo.
- [ ] 2.2 Document dev commands: `alembic upgrade head`, `alembic downgrade` to the revision before Phase 1 (or `base`), and first-time empty Postgres setup.

## 3. Initial Postgres migration

- [ ] 3.1 Author initial migration creating tables per [architecture/db_schema.md](../../../architecture/db_schema.md) §3: `media_outlets`, `categories`, `articles` (no FK on `topic_id`), `article_analysis`, `article_entities`, `topics`, `topic_versions`, `topic_article_links`, `media_aggregates`, `api_request_logs`, with constraints and cascades as in the SQL snippets.
- [ ] 3.2 Add all indexes from §4 in the same migration chain.
- [ ] 3.3 Verify upgrade on empty DB and downgrade path for dev.

## 4. SQLAlchemy models

- [ ] 4.1 Define SQLAlchemy models (or Core tables) matching the migrated schema for all Phase 1 tables; expose a single import surface for services.
- [ ] 4.2 Align types for JSONB columns, `NUMERIC` precision, timestamps with time zone, and enum-like `VARCHAR` fields per architecture notes.

## 5. Qdrant collections and configuration

- [ ] 5.1 Add configuration for Qdrant URL, optional API key, collection names (`article_embeddings`, `topic_embeddings`), vector size, and distance metric, documented as MUST match the embedding model used for articles and topics.
- [ ] 5.2 Implement idempotent collection create/get with configured vector params; document point-ID strategy: use `article_id` / `topic_id` as Qdrant point ids for upserts.
- [ ] 5.3 Define payload field names and types for §5.1 and §5.2 (shared constants or schema doc in code) so future writers stay consistent.

## 6. Verification

- [ ] 6.1 Smoke-test: migrate Postgres, run collection bootstrap against dev Qdrant, confirm collections exist with expected vector settings.
- [ ] 6.2 Ensure no scope creep: no `/ingest`, dedupe service, workers, embedding calls, LangGraph, Next.js, or read APIs in this change.

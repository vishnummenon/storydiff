## Context

StoryDiff Phase 1 (per [architecture/build_order.md](../../../architecture/build_order.md)) starts with relational schema and Qdrant collections before ingest APIs or workers. [architecture/db_schema.md](../../../architecture/db_schema.md) defines prototype v1 Postgres tables, indexes, and Qdrant collection contracts. [architecture/implementation_choices.md](../../../architecture/implementation_choices.md) commits to SQLAlchemy and Alembic. Backend language for this change is Python; persistence uses SQLAlchemy; schema evolution uses Alembic; Qdrant uses `qdrant-client` (or the official equivalent). No alternate ORMs or migration tools are introduced.

## Goals / Non-Goals

**Goals:**

- Ship an empty-to-full Alembic migration path for all Phase 1 tables and §4 indexes, plus SQLAlchemy definitions importable from one package.
- Establish Qdrant collections `article_embeddings` and `topic_embeddings` with explicit vector size and distance configuration and documented point-ID strategy for idempotent upserts.
- Wire configuration via environment (and optional local-only example files excluded from secrets), never committing credentials.

**Non-Goals:**

- `/ingest`, dedupe/upsert logic, queues, workers, embedding generation, LangGraph, Next.js, read APIs, hybrid search ranking formulas, or topic embedding strategy experiments beyond documenting v1 alignment (title + summary per implementation choices for later phases).

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| ORM & migrations | SQLAlchemy + Alembic only | Matches `implementation_choices.md`; single toolchain for models and revisions. |
| Driver | `psycopg` (v3) unless repo standard differs | Common async/sync pairing with SQLAlchemy 2.x; pick what the scaffold uses. |
| Migration layout | One initial revision (or split create/index only if file size demands) | Empty DB → full schema; §4 indexes in same revision as tables or immediately following in the same chain. |
| `articles.topic_id` | No FK in v1 | Architecture doc does not declare a FK; canonical membership is `topic_article_links`. |
| `processing_status` / topic `status` | `VARCHAR` with documented enum-like strings | Matches architecture SQL; validation in application layers in later changes. |
| Qdrant distance | Configurable; default **Cosine** in docs if unset | Typical for normalized embedding models; operators may set **Dot** or **Euclid** to match their model vendor. |
| Vector dimensions | Configurable integer (e.g. `EMBEDDING_VECTOR_SIZE`) | Must match the embedding model output for both article and topic pipelines. |
| Qdrant point ids | **Unsigned integer point id = domain id** (`article_id`, `topic_id`) | Idempotent `upsert` by id; matches BIGINT ids from Postgres; Qdrant accepts integer ids. Document if the client requires wrapping unsigned range. |
| `api_request_logs` | Included in initial migration | User requested inclusion unless explicitly deferred; supports later observability without a follow-up migration for the table shell. |
| Qdrant bootstrap | Script or app init that creates collections if missing | Collections are not Postgres DDL; idempotent `get_or_create` pattern with configured vector params and payload index strategy deferred to implementation (minimal in Phase 1). |

**Alternatives considered:**

- **UUID point ids:** Rejected for v1—adds mapping table or extra payload lookups; integer id matches architecture examples.
- **Separate migration tool (e.g. raw SQL only):** Rejected—violates non-negotiable Alembic stack.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Embedding model dimension mismatch | Document loudly that `EMBEDDING_VECTOR_SIZE` and distance MUST match the model; add startup validation that refuses wrong-sized writes in later phases. |
| Qdrant and Postgres id divergence | Enforce single source of truth from Postgres ids for point ids; never autogenerate Qdrant-only ids for article/topic rows. |
| Large `raw_text` on `articles` | Accept per implementation choice (store full text); monitor table bloat and TOAST in ops later—not Phase 1 scope. |

## Migration Plan

1. Add Python project layout (if not present): dependencies `sqlalchemy`, `alembic`, `psycopg`, `qdrant-client`.
2. Configure Alembic `env.py` to read `DATABASE_URL` (or `SQLALCHEMY_DATABASE_URI`) from the environment; document `.env.example` without real secrets.
3. Author initial Alembic revision: `CREATE TABLE` for all §3 entities in dependency order; `CREATE INDEX` for §4; include `api_request_logs`.
4. Add SQLAlchemy `Base` and models mirroring the revision; run `alembic check` / compare in CI when available.
5. Document dev commands: `alembic upgrade head`, `alembic downgrade base` (or previous revision), and first-time Postgres creation.
6. Implement Qdrant collection helper: read `QDRANT_URL`, `QDRANT_API_KEY` (optional), `QDRANT_ARTICLE_EMBEDDINGS_COLLECTION`, `QDRANT_TOPIC_EMBEDDINGS_COLLECTION` (or fixed names `article_embeddings` / `topic_embeddings`), `EMBEDDING_VECTOR_SIZE`, `QDRANT_DISTANCE_METRIC`—create collections with matching vector size and distance.

**Rollback:** `alembic downgrade` for Postgres; Qdrant drops collections manually or via script if collections must be removed (destructive).

## Open Questions

- Exact Python package layout and module path for models (`src/storydiff/db/` vs. `app/models/`)—follow whatever the repo adopts when `/opsx:apply` runs.
- Whether to add Alembic autogenerate workflow or rely on explicit migrations only (explicit preferred for first revision).

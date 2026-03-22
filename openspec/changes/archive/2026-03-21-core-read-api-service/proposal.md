## Why

The backend persists analyzed articles, topics, aggregates, and embeddings, and already exposes write-side ingestion (`POST /api/v1/ingest`), but there is no **read-optimized HTTP surface** for the frontend/BFF. Without feed, topic detail, media analytics, search, and timeline endpoints, `architecture/build_order.md` (“Implement read APIs”) and [architecture/hld.md](../../../architecture/hld.md) §4.5 / §12 cannot be satisfied.

## What Changes

- Add a **`storydiff.core_api`** package: FastAPI routers, Pydantic models, and **query/service** modules that perform **read-only** SQLAlchemy queries and (where required) Qdrant vector search—no ingestion writes, no LangGraph analysis execution.
- Expose contract-aligned routes under **`/api/v1`**: **`GET /feed`**, **`GET /topics/{topicId}`**, **`GET /topics/{topicId}/timeline`**, **`GET /media`**, **`GET /media/{mediaId}`**, **`GET /search`**, and **`GET /categories`** (recommended parity with [architecture/api_contract.md](../../../architecture/api_contract.md) §8.7).
- Use the common JSON envelope **`{ "data", "meta", "error" }`** for success and structured errors, consistent with [architecture/api_contract.md](../../../architecture/api_contract.md) and existing **`storydiff.ingestion.envelope`** helpers.
- Add automated tests: **`httpx` / `TestClient`** API tests (skipping when `TEST_DATABASE_URL` unset, mirroring ingest tests), plus focused unit tests for search routing/SQL helpers where valuable.
- **Explicitly unchanged in this change:** **`GET /health`** remains the existing simple JSON at **`/health`** (not moved under `/api/v1`, not wrapped in the §8.9 envelope) unless a follow-up change standardizes health across the app.

## Capabilities

### New Capabilities

- `core-read-api`: Read-only Core API HTTP contract (envelope, routes §8.2–8.8 behavior, 404/error codes, query parameters, Postgres and Qdrant read paths as specified).

### Modified Capabilities

- _(none — this change adds HTTP read behavior; underlying data specs in `openspec/specs/` remain the source of truth for persisted entities.)_

## Impact

- **`backend/src/storydiff/`**: new `core_api/` package; **`storydiff.main:app`** registers the read router(s) alongside ingestion.
- **Dependencies**: reuse **`fastapi`**, **`sqlalchemy`**, **`qdrant-client`**; may add a small embedding helper dependency or reuse existing analysis embedding utilities for semantic search (see design).
- **Runtime**: Postgres required for keyword paths and relational joins; Qdrant required for semantic/hybrid search modes when enabled.
- **Docs**: satisfies **`architecture/build_order.md`** read-API line for this slice; implementation tracks [architecture/api_contract.md](../../../architecture/api_contract.md) §8.2–8.8.

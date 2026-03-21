## 1. Package scaffold and wiring

- [x] 1.1 Add `storydiff.core_api` package (`__init__.py`, shared `schemas` for envelope-wrapped responses if needed)
- [x] 1.2 Register Core Read router(s) in `storydiff.main` under prefix `/api/v1` (alongside ingestion router)
- [x] 1.3 Add FastAPI dependencies for DB session (`get_db`) and optional Qdrant client / embedding helper as per design

## 2. Shared HTTP helpers

- [x] 2.1 Implement or reuse exception-to-envelope mapping for `TOPIC_NOT_FOUND`, `MEDIA_NOT_FOUND` (HTTP 404) consistent with `storydiff.ingestion.envelope`
- [x] 2.2 Add Pydantic response models aligned with [architecture/api_contract.md](../../../architecture/api_contract.md) §8.2–8.8 field names

## 3. Feed and categories

- [x] 3.1 Implement `GET /api/v1/categories` (active categories, `display_order`)
- [x] 3.2 Implement `GET /api/v1/feed` with `category`, `limit_per_category`, `include_empty_categories` and nested topic tiles from `topics` + `categories`

## 4. Topic detail and timeline

- [x] 4.1 Implement `GET /api/v1/topics/{topicId}` with `include_articles`, `include_timeline_preview`, joins to `topic_article_links`, `articles`, `media_outlets`, `article_analysis`
- [x] 4.2 Implement `GET /api/v1/topics/{topicId}/timeline` from `topic_versions` with ordered `versions`

## 5. Media analytics

- [x] 5.1 Implement `GET /api/v1/media` using `media_aggregates` with window parsing and fallback aggregation from `articles` / `article_analysis` when needed
- [x] 5.2 Implement `GET /api/v1/media/{mediaId}` with overall metrics, `by_category`, and `recent_topics`

## 6. Search

- [x] 6.1 Implement keyword search over Postgres (`q`, `category`, `from`/`to`, `type`, `limit`)
- [x] 6.2 Implement semantic search via Qdrant `article_embeddings` / `topic_embeddings` using query embedding (shared model settings with analysis pipeline)
- [x] 6.3 Implement hybrid mode merging keyword and semantic results with a documented merge strategy in code

## 7. Tests and docs

- [x] 7.1 Add API tests under `tests/` using `TestClient` / httpx; skip when `TEST_DATABASE_URL` unset (mirror ingest API tests)
- [x] 7.2 Add unit tests for search mode dispatch and window/sort parsing where logic is non-trivial
- [x] 7.3 Update `backend/README.md` with read API examples (curl or paths) for local `uvicorn`

## Context

StoryDiff’s FastAPI app (`storydiff.main`) already mounts **`POST /api/v1/ingest`**. Postgres holds **`categories`**, **`topics`**, **`topic_versions`**, **`topic_article_links`**, **`articles`**, **`article_analysis`**, **`media_outlets`**, and **`media_aggregates`** (see `storydiff.db.models`). Qdrant collections **`article_embeddings`** and **`topic_embeddings`** are created via `storydiff.qdrant.collections.ensure_collections()` with point IDs equal to Postgres `article_id` / `topic_id`.

The Core Read API is a **thin HTTP + service layer**: map [architecture/api_contract.md](../../../architecture/api_contract.md) §8.2–8.8 onto queries and aggregations. **Read code must not import or invoke LangGraph** (`storydiff.analysis.graph`) or analysis workers.

## Goals / Non-Goals

**Goals:**

- Implement all listed **GET** routes under **`/api/v1`** with the **common success/error envelope** (`storydiff.ingestion.envelope` patterns).
- Feed, topic detail, timeline, media list/detail, categories, and search (keyword / semantic / hybrid) per contract shapes and query parameters.
- **404** with structured error for unknown **`topicId`** / **`mediaId`** where applicable.
- Tests: API tests against real Postgres when `TEST_DATABASE_URL` is set; skip otherwise.

**Non-Goals:**

- Authentication, rate limiting, Redis caching, GraphQL, write APIs.
- Changing **`GET /health`** at **`/health`** to the §8.9 envelope (leave as-is for operational simplicity unless product asks for a single envelope everywhere).
- Reindexing or backfilling Qdrant (assumes existing indexing pipeline maintains vectors).

## Decisions

### D1 — URL prefix

**Choice:** Mount read routes at **`/api/v1`** (e.g. **`GET /api/v1/feed`**) to match the existing ingest prefix and [architecture/api_contract.md](../../../architecture/api_contract.md) “Base Path Suggestion”.

**Alternatives:** Root paths (`/feed`) — rejected to avoid mixing versioned and unversioned APIs.

### D2 — Package layout

**Choice:** **`storydiff.core_api`** with submodules such as **`router.py`**, **`schemas.py`**, **`deps.py`**, **`services/`** or **`queries/`** per aggregate (feed, topic, media, search).

**Rationale:** Mirrors `storydiff.ingestion`; keeps routers free of SQL beyond trivial mapping.

### D3 — Envelope and errors

**Choice:** Reuse **`success_response`** / **`error_response`** from `storydiff.ingestion.envelope`. Use HTTP **404** for not-found domain entities with **`error.code`** such as **`TOPIC_NOT_FOUND`** / **`MEDIA_NOT_FOUND`** (align with contract examples).

### D4 — Feed and topic field mapping

**Choice:** Map **`Topic.current_title`** / **`Topic.current_summary`** to contract **`title`** / **`summary`**; **`Topic.updated_at`** drives **`last_updated_at`** in feed/topic payloads. **`reliability_score`** comes from **`Topic.current_reliability_score`**.

### D5 — Topic articles and scores

**Choice:** List articles via **`topic_article_links`** joined to **`articles`**, **`media_outlets`**, and **`article_analysis`**. Expose analysis metrics under a nested **`scores`** object per §8.3. Map **`polarity_labels_json`** to a string array **`polarity_labels`** (empty list if null).

### D6 — Timeline

**Choice:** **`GET /topics/{topicId}/timeline`** reads **`topic_versions`** ordered by **`version_no`**. **`GET /topics/{topicId}`** embeds a **preview** from the latest N versions (e.g. last 3–5) when **`include_timeline_preview`** is true.

### D7 — Media leaderboard and detail

**Choice:** Prefer **`media_aggregates`** filtered by **`window_start`/`window_end`** derived from the **`window`** query param (e.g. **`30d`** → rolling window ending **now**). When a row is missing for a publisher/category combo, fall back to **live aggregation** from **`articles`** + **`article_analysis`** in the same window (documented in implementation). **`GET /media/{mediaId}`** joins outlet row + aggregates + recent topics from **`topics`** / **`articles`** as needed.

### D8 — Search

**Choice:**

- **Keyword:** SQL `ILIKE` / `to_tsvector` (if indexed) over **`topics.current_title`**, **`topics.current_summary`**, **`articles.title`**, **`articles.snippet`** with optional **`category`** and **`published_at`** bounds.
- **Semantic:** Embed **`q`** with the **same dimensionality** as `EMBEDDING_VECTOR_SIZE`; query Qdrant **`topic_embeddings`** and **`article_embeddings`** with score thresholds; merge by id.
- **Hybrid:** Run both, merge with a documented strategy (e.g. weighted score or RRF-lite) in code.

**Embedding source:** Reuse or factor out embedding call used elsewhere (e.g. analysis) so read path does not fork model choice. If no shared helper exists, add a minimal **`core_api.embeddings`** module reading model/env from existing analysis settings.

### D9 — Categories

**Choice:** **`GET /api/v1/categories`** returns **`categories`** where **`is_active`** is true, ordered by **`display_order`**.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| **Empty Qdrant** or stale vectors | Semantic modes return empty or degraded results; document; optional health of search in `meta` later |
| **`media_aggregates` sparse** | Fallback SQL aggregation for leaderboard/detail |
| **Hybrid scoring arbitrary** | Start with simple merge; tune later; document formula in code comments |
| **N+1 queries on feed** | Use joinedload / grouped queries; add indexes if slow (out of scope unless measured) |

## Migration Plan

1. Ship read routers behind existing app (no flag).
2. Run migrations: **none** required if schema already contains listed tables.
3. **Rollback:** Remove router include from `main.py` and delete `core_api` package (no DB rollback).

## Open Questions

- Whether **full-text search** on Postgres should use **GIN/tsvector** migrations in a follow-up (v1 can use `ILIKE` for simplicity).
- Exact **hybrid merge** formula and whether to expose component scores in **`meta`**.

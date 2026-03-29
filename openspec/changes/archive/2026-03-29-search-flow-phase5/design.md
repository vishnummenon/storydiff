## Context

The `GET /api/v1/search` endpoint and `/search` frontend page exist from Phase 4 scaffolding. The backend keyword path uses `ilike` (`%q%`) — a sequential scan with no index support. The HLD specifies Postgres full-text search. The frontend exposes mode and result-type selectors but not the category or date-range filters already accepted by the API. Test coverage is a single smoke test.

Three bounded changes are needed: upgrade keyword search to FTS, add filter UI, expand tests.

## Goals / Non-Goals

**Goals:**
- Keyword search uses Postgres `tsvector`/`GIN` indexes and `plainto_tsquery` — no sequential scans
- Frontend exposes `category`, `from`, and `to` filters alongside the existing `mode` and `type` selectors
- Six new integration tests exercise real data paths and validate error cases

**Non-Goals:**
- Entity-name FTS (article_entities table) — deferred; adds complexity with marginal gain for prototype
- Semantic / hybrid test coverage against live Qdrant — requires infra not available in test env
- Freshness score boosting in hybrid ranking — the current `merge_hybrid_scores` weighting is sufficient for prototype
- Search result pagination

## Decisions

### 1. FTS via generated stored columns + GIN, not triggers

**Decision**: Add `GENERATED ALWAYS AS (to_tsvector('english', coalesce(title, ''))) STORED` column to `articles`, and `GENERATED ALWAYS AS (to_tsvector('english', coalesce(current_title,'') || ' ' || coalesce(current_summary,''))) STORED` to `topics`. Create GIN indexes on both. Update `search_service.py` to use `col.op('@@')(func.plainto_tsquery('english', q))`.

**Alternatives considered**:
- *Trigger-maintained tsvector*: more flexible (can index multiple columns later) but requires a PL/pgSQL trigger — overkill for prototype and harder to migrate cleanly.
- *Keep ilike*: zero migration cost but forces a sequential scan on every keyword search; unacceptable as article volume grows.
- *SQLAlchemy `func.to_tsvector` inline (no stored column)*: avoids migration but recalculates on every query — no GIN index benefit.

**Why stored column**: single migration, GIN index is automatic, query code stays simple.

### 2. Alembic migration with `server_default` pattern for generated columns

Generated columns require raw DDL (`op.execute`) since SQLAlchemy's `Column` API does not support `GENERATED ALWAYS AS … STORED` syntax. The migration is additive; downgrade drops the columns.

### 3. Frontend filters added to SearchPanel props, not fetched client-side

**Decision**: `search/page.tsx` fetches categories server-side (same pattern as `page.tsx` fetching the feed) and passes them as a `categories` prop to `SearchPanel`. `from`/`to` are plain ISO date strings passed as `initialFrom`/`initialTo`.

**Alternative**: Fetch categories inside `SearchPanel` on mount via `useEffect`. Rejected — breaks the existing SSR-first pattern, adds a flash of empty dropdown, and complicates the URL restore logic.

### 4. Tests use `sample_feed_data` fixture; semantic/hybrid paths use `None` Qdrant injection

The test client overrides the `get_qdrant_client_optional` dependency to return `None`. Semantic/hybrid tests assert the 503 `SEARCH_UNAVAILABLE` path — no Qdrant mock needed.

## Risks / Trade-offs

- [Generated column syntax varies by Postgres version] → Migration targets Postgres 12+ (`GENERATED ALWAYS AS … STORED` available since 12). Docker Compose uses Postgres 15 — no risk.
- [FTS ranking is unweighted] → `plainto_tsquery` returns a boolean match; no `ts_rank` ordering yet. Results are ordered by `last_seen_at` (topics) and `published_at` (articles). Acceptable for prototype; rank ordering can be layered in Phase 6.
- [Frontend date inputs produce local-timezone ISO strings] → `<input type="date">` gives `YYYY-MM-DD`; the API's `_parse_iso_dt` handles bare dates as datetime strings via `fromisoformat`. Acceptable — time-of-day precision is not required for date-range filtering.

## Migration Plan

1. `uv run alembic upgrade head` applies the new migration (additive DDL only)
2. No data backfill needed — generated columns populate automatically on upgrade
3. Rollback: `uv run alembic downgrade -1` drops the two `tsvector` columns and GIN indexes

## Open Questions

- None — scope is fully bounded by the three gaps identified in the proposal.

## Why

The `/api/v1/search` endpoint and `/search` frontend page were scaffolded during Phase 4, but keyword search uses `ilike` pattern matching instead of Postgres full-text search, the UI exposes no category or date filters, and test coverage is a single smoke test with no data. Closing these gaps completes Phase 5 search as specified in the HLD.

## What Changes

- Alembic migration adds `tsvector` generated columns and GIN indexes to `articles` (on `title`) and `topics` (on `current_title + current_summary`) for Postgres FTS
- `_kw_topic` and `_kw_articles` in `search_service.py` switch from `ilike` to `plainto_tsquery` / `@@` operator
- `SearchPanel.tsx` gains a category dropdown and `from`/`to` date inputs
- `search/page.tsx` fetches categories server-side and reads `from`/`to` from `searchParams`, passing all filters into the initial API call and populating panel props
- `test_core_read_api.py` gains six new tests covering keyword results, category filter, date range filter, invalid mode (422), and semantic without Qdrant (503)

## Capabilities

### New Capabilities

- `search`: Full-text keyword search over articles and topics, plus category and date-range filter exposure in the frontend

### Modified Capabilities

- `core-read-api`: The `GET /search` keyword path now uses Postgres FTS instead of `ilike`; response contract is unchanged

## Impact

- **Backend**: `search_service.py`, new Alembic migration file
- **Frontend**: `web/app/search/page.tsx`, `web/app/search/SearchPanel.tsx`
- **Tests**: `backend/tests/core_api/test_core_read_api.py`
- **DB**: Two new `tsvector` generated columns + GIN indexes (additive, no data loss)
- **No API contract changes** — all new filter params were already accepted by the endpoint

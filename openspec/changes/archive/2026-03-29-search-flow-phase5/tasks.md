## 1. Database Migration (FTS columns + GIN indexes)

- [x] 1.1 Generate a new Alembic migration file (`uv run alembic revision --autogenerate -m "add fts tsvector columns"` or blank revision)
- [x] 1.2 In the migration `upgrade()`, use `op.execute()` to add `search_vector GENERATED ALWAYS AS (to_tsvector('english', coalesce(title, ''))) STORED` column to `articles`
- [x] 1.3 In the same `upgrade()`, create a GIN index on `articles.search_vector`
- [x] 1.4 Add `search_vector GENERATED ALWAYS AS (to_tsvector('english', coalesce(current_title,'') || ' ' || coalesce(current_summary,''))) STORED` column to `topics`
- [x] 1.5 Create a GIN index on `topics.search_vector`
- [x] 1.6 Implement `downgrade()` to drop the two GIN indexes and the two `search_vector` columns
- [x] 1.7 Run `uv run alembic upgrade head` against the dev database and verify the columns and indexes exist

## 2. Backend — Upgrade Keyword Search to FTS

- [x] 2.1 In `backend/src/storydiff/core_api/services/search_service.py`, update `_kw_topic` to replace the `ilike` filter with `Topic.search_vector.op('@@')(func.plainto_tsquery('english', q))`
- [x] 2.2 Update `_kw_articles` to replace the `ilike` filter with `Article.search_vector.op('@@')(func.plainto_tsquery('english', q))`
- [x] 2.3 Add `from sqlalchemy import func` import if not already present
- [x] 2.4 Verify that the SQLAlchemy `Topic` and `Article` models in `db/models.py` expose the `search_vector` column (add `Column(TSVector)` mapped attribute if needed, using `sqlalchemy.dialects.postgresql.TSVECTOR`)

## 3. Test Coverage — Search Endpoint

- [x] 3.1 In `backend/tests/core_api/test_core_read_api.py`, add `test_search_keyword_returns_topic` — use the `sample_feed_data` fixture, query a word from the topic title, assert the topic appears in `results.topics`
- [x] 3.2 Add `test_search_keyword_returns_article` — use `sample_feed_data`, query a word from the article title, assert the article appears in `results.articles`
- [x] 3.3 Add `test_search_keyword_category_filter` — query with the topic title word but pass a non-matching `category` slug, assert `results.topics` is empty
- [x] 3.4 Add `test_search_keyword_date_range_filter` — query with a matching article title word but pass `from`/`to` that excludes the article's `published_at`, assert `results.articles` is empty
- [x] 3.5 Add `test_search_invalid_mode_returns_422` — call `/api/v1/search?q=test&mode=garbage`, assert HTTP 422 and `error.code == "VALIDATION_ERROR"`
- [x] 3.6 Add `test_search_semantic_without_qdrant_returns_503` — call `/api/v1/search?q=test&mode=semantic` (the test client has no Qdrant configured), assert HTTP 503 and `error.code == "SEARCH_UNAVAILABLE"`
- [x] 3.7 Run `uv run pytest tests/core_api/test_core_read_api.py` and confirm all tests pass

## 4. Frontend — Category and Date Filters in SearchPanel

- [x] 4.1 In `web/app/search/SearchPanel.tsx`, add `categories: { slug: string; name: string }[]`, `initialCategory: string`, `initialFrom: string`, and `initialTo: string` to the component props interface
- [x] 4.2 Add `category`, `from`, and `to` state variables (initialized from the corresponding `initial*` props)
- [x] 4.3 Add a category `<select>` dropdown (with a blank "All categories" option) following the same pattern as the mode selector
- [x] 4.4 Add `<input type="date">` for `from` and `to` with appropriate labels, matching the existing input styling
- [x] 4.5 Update the `params` construction in `run()` to include `category`, `from`, and `to` when they are non-empty
- [x] 4.6 Update the `router.replace` URL to include all active filter params
- [x] 4.7 In `web/app/search/page.tsx`, fetch categories server-side using `apiGet('/api/v1/categories', { cache: 'no-store' })` (wrapped in try/catch; fall back to empty array on error)
- [x] 4.8 Read `from` and `to` from `searchParams` and pass as `initialFrom`/`initialTo` to `SearchPanel`
- [x] 4.9 Include `category`, `from`, and `to` in the initial server-side API call when present
- [x] 4.10 Pass the fetched `categories` array (`.data.categories` mapped to `{slug, name}`) as a prop to `SearchPanel`
- [x] 4.11 Run `npm run build` in `web/` to confirm no TypeScript errors

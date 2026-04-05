## 1. Setup

- [x] 1.1 Add `feedparser` and `trafilatura` dependencies to `pyproject.toml`
- [x] 1.2 Create module structure: `backend/src/storydiff/rss/__init__.py`, `config.py`, `fetcher.py`, `extractor.py`, `__main__.py`
- [x] 1.3 Add RSS-related settings to environment config (`API_BASE_URL`, `RSS_POLL_INTERVAL`, `RSS_FETCH_DELAY`)

## 2. Feed Configuration

- [x] 2.1 Implement `config.py` — Pydantic models for feed config schema (url, outlet_slug, category, label, source_map) and YAML loader with validation
- [x] 2.2 Create initial `backend/feeds.yaml` with a curated set of feeds (Google News topic queries, major outlet category feeds)

## 3. RSS Parsing

- [x] 3.1 Implement RSS polling in `fetcher.py` — use feedparser to fetch and parse each configured feed URL
- [x] 3.2 Map RSS entry fields to IngestRequest shape (title, url, canonical_url, published_at, snippet, media_outlet_slug, source_category)
- [x] 3.3 Handle missing published date (fallback to current UTC time)
- [x] 3.4 Implement Google News outlet resolution — parse `<source>` tag, apply source_map lookup, fallback to slugified source name

## 4. Full-Text Extraction

- [x] 4.1 Implement `extractor.py` — fetch article URL and extract body text using trafilatura
- [x] 4.2 Add per-domain rate limiting (configurable delay, default 2s)
- [x] 4.3 Set descriptive User-Agent header on outbound requests
- [x] 4.4 Handle extraction failures gracefully — return None for raw_text, log warning

## 5. Ingest Submission

- [x] 5.1 Implement HTTP client to POST each article to `/api/v1/ingest`
- [x] 5.2 Handle success responses — log article_id and dedupe_status
- [x] 5.3 Handle error responses — log and continue to next article
- [x] 5.4 Handle duplicate_ignored as normal outcome

## 6. Worker Entry Point

- [x] 6.1 Implement `__main__.py` with CLI argument parsing (--loop, --config, --interval)
- [x] 6.2 One-shot mode: poll all feeds once, submit articles, exit
- [x] 6.3 Loop mode: poll feeds repeatedly at configured interval

## 7. Testing

- [x] 7.1 Unit tests for feed config loading and validation (valid config, missing fields)
- [x] 7.2 Unit tests for RSS entry → IngestRequest mapping (standard entry, missing pubdate, Google News source resolution)
- [x] 7.3 Unit tests for full-text extraction (success, failure fallback)
- [x] 7.4 Integration test for end-to-end flow with mocked HTTP responses (RSS feed XML → ingest API call)

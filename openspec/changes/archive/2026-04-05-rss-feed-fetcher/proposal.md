## Why

StoryDiff currently relies on manually seeded data. To deliver real-time narrative variance analysis, we need automated ingestion of live news articles from diverse sources. RSS feeds are the most accessible, structured, and widely supported mechanism for this — nearly every major news outlet publishes topic-specific feeds, and Google News RSS enables keyword-driven filtering (e.g., "Kerala elections", "West Asia conflict").

## What Changes

- Add a new **RSS feed fetcher** module (`storydiff/rss/`) that polls configured RSS feeds on a schedule, extracts article metadata, fetches full article text, and submits each article to the existing `POST /api/v1/ingest` endpoint.
- Add a **feed configuration file** (`feeds.yaml`) defining feed URLs, outlet slugs, and optional categories.
- Introduce two new dependencies: `feedparser` (RSS parsing) and `trafilatura` (full-text extraction from article URLs).
- Add a new **scheduled worker** entry point (`python -m storydiff.rss`) that can run as a periodic background task or cron-triggered Lambda.

## Capabilities

### New Capabilities
- `rss-feed-fetcher`: RSS polling, article metadata extraction, full-text fetching, and submission to the ingest pipeline. Includes feed configuration, rate limiting, and error handling.

### Modified Capabilities
<!-- No existing spec-level requirements are changing. The fetcher is a new producer that uses the existing ingest API as-is. -->

## Impact

- **New code**: `storydiff/rss/` module (fetcher, config loader, text extractor)
- **New config**: `feeds.yaml` at backend root (or `storydiff/rss/feeds.yaml`)
- **Dependencies**: `feedparser`, `trafilatura` added to `pyproject.toml`
- **Infrastructure**: Optionally a new Lambda handler or EventBridge rule for scheduled execution
- **Existing systems**: No changes — the fetcher is a pure producer to the existing ingest endpoint; deduplication, analysis, and topic assignment remain untouched

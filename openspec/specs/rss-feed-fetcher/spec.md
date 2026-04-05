# rss-feed-fetcher Specification

## Purpose
RSS feed fetcher module — polls configured RSS feeds, extracts article metadata and full text, and submits articles to the ingest pipeline.

## Requirements

### Requirement: Feed configuration file defines RSS sources

The system SHALL load feed definitions from a YAML configuration file (`backend/feeds.yaml`). Each feed entry SHALL include `url` (required), `outlet_slug` (required), and optionally `category` and `label`. The system SHALL validate the configuration at startup and reject entries missing required fields.

#### Scenario: Valid feed config loads successfully
- **WHEN** the fetcher starts with a valid `feeds.yaml` containing multiple feed entries
- **THEN** the system SHALL parse all entries and use them for polling

#### Scenario: Missing required field rejected
- **WHEN** a feed entry omits `url` or `outlet_slug`
- **THEN** the system SHALL log an error for that entry and skip it without crashing

### Requirement: RSS feed polling extracts article metadata

The system SHALL poll each configured feed URL using `feedparser`, and for each entry SHALL extract `title`, `link` (as `url` and `canonical_url`), `published` (as `published_at`), and `description` (as `snippet`). The system SHALL use the feed config's `outlet_slug` as `media_outlet_slug` and `category` as `source_category`.

#### Scenario: Standard RSS entry mapped to ingest fields
- **WHEN** an RSS entry contains `<title>`, `<link>`, `<pubDate>`, and `<description>`
- **THEN** the system SHALL map these to `title`, `url`/`canonical_url`, `published_at`, and `snippet` respectively

#### Scenario: Missing published date uses current time
- **WHEN** an RSS entry has no `<pubDate>` or equivalent
- **THEN** the system SHALL use the current UTC timestamp as `published_at`

### Requirement: Full article text extraction from URL

For each article discovered via RSS, the system SHALL attempt to fetch and extract the full article body text from the article URL using `trafilatura`. The extracted text SHALL be submitted as `raw_text` in the ingest request.

#### Scenario: Successful text extraction
- **WHEN** trafilatura successfully extracts text from an article URL
- **THEN** the system SHALL include the extracted text as `raw_text` in the ingest payload

#### Scenario: Text extraction failure falls back to snippet
- **WHEN** trafilatura fails to extract text (network error, paywall, unsupported page)
- **THEN** the system SHALL submit the article with `raw_text` set to `None` and `snippet` populated from RSS

### Requirement: Articles submitted to ingest API

The system SHALL submit each discovered article to `POST /api/v1/ingest` as a JSON payload conforming to the `IngestRequest` schema. The system SHALL use the API base URL from configuration (environment variable `API_BASE_URL`, default `http://127.0.0.1:8000`).

#### Scenario: Successful submission
- **WHEN** the ingest API returns a success response
- **THEN** the system SHALL log the `article_id` and `dedupe_status`

#### Scenario: Duplicate article handled gracefully
- **WHEN** the ingest API returns `dedupe_status: duplicate_ignored`
- **THEN** the system SHALL treat this as a normal outcome and continue processing

#### Scenario: Ingest API error does not halt the batch
- **WHEN** the ingest API returns an error for one article
- **THEN** the system SHALL log the error and continue processing remaining articles

### Requirement: Rate limiting and politeness

The system SHALL enforce a configurable delay between full-text fetch requests to the same domain (default: 2 seconds). The system SHALL set a descriptive `User-Agent` header on all outbound HTTP requests for text extraction.

#### Scenario: Same-domain requests are throttled
- **WHEN** two consecutive articles are from the same domain
- **THEN** the system SHALL wait at least the configured delay before fetching the second article's full text

### Requirement: Worker execution modes

The system SHALL be runnable via `python -m storydiff.rss`. In **one-shot mode** (default), it SHALL poll all feeds once and exit. With the `--loop` flag, it SHALL poll feeds repeatedly at a configurable interval (default: 15 minutes).

#### Scenario: One-shot mode exits after single poll
- **WHEN** the worker runs without `--loop`
- **THEN** it SHALL poll all configured feeds once, submit discovered articles, and exit with code 0

#### Scenario: Loop mode polls repeatedly
- **WHEN** the worker runs with `--loop`
- **THEN** it SHALL poll all feeds, wait for the configured interval, and poll again indefinitely

### Requirement: Google News outlet resolution

When using Google News RSS feeds, the system SHALL attempt to resolve the originating outlet from the RSS entry's `<source>` tag. It SHALL map known source names to `media_outlet_slug` values via an optional `source_map` in the feed config. Unknown sources SHALL be slugified (lowercase, hyphens) as the fallback slug.

#### Scenario: Known source maps to configured slug
- **WHEN** a Google News entry has `<source>Reuters</source>` and the feed config maps "Reuters" to `reuters`
- **THEN** `media_outlet_slug` SHALL be `reuters`

#### Scenario: Unknown source slugified
- **WHEN** a Google News entry has `<source>The Kerala Times</source>` with no configured mapping
- **THEN** `media_outlet_slug` SHALL be `the-kerala-times`

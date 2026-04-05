## Context

StoryDiff ingests news articles via `POST /api/v1/ingest`, which handles deduplication, persistence, and triggers the analysis pipeline via SQS. Currently, articles are populated using a seed data script. To enable real-time narrative analysis, we need an automated producer that fetches live articles from RSS feeds and submits them through the existing ingest endpoint.

The fetcher is a **pure producer** — it sits upstream of the ingest API and requires no changes to the existing pipeline. RSS feeds are widely available from major outlets (AP, Reuters, BBC, Al Jazeera, NDTV, The Hindu, etc.) and Google News RSS supports keyword-based topic filtering.

## Goals / Non-Goals

**Goals:**
- Automatically poll RSS feeds and submit discovered articles to the ingest API
- Support topic-specific feeds (e.g., "Kerala elections", "West Asia") via curated feed URLs and Google News RSS search queries
- Extract full article text from linked URLs to populate `raw_text`
- Be configurable via a YAML file — no code changes needed to add/remove feeds
- Handle failures gracefully (network errors, extraction failures, paywalled content)
- Be runnable as a CLI worker, cron job, or Lambda

**Non-Goals:**
- Modifying the existing ingest API or analysis pipeline
- Handling JavaScript-rendered pages (SPAs) — trafilatura covers static/SSR pages which is sufficient for news sites
- Building a feed management UI
- Paywall bypass or authentication with news sources
- Real-time streaming (WebSub/PubSubHubbub) — periodic polling is sufficient for v1

## Decisions

### 1. Feed configuration via YAML file

Store feed definitions in `backend/feeds.yaml`. Each entry specifies the feed URL, outlet slug, and optional category override.

**Why over DB-backed config:** Feeds change rarely. YAML is version-controlled, reviewable, and requires no migration. Can move to DB later if dynamic management is needed.

**Why over JSON:** YAML supports comments, making it easier to organize feeds by region/topic with inline notes.

```yaml
feeds:
  - url: "https://news.google.com/rss/search?q=kerala+elections&hl=en-IN"
    outlet_slug: "google-news"
    category: "politics"
    label: "Kerala Elections"

  - url: "https://www.aljazeera.com/xml/rss/all.xml"
    outlet_slug: "al-jazeera"
    category: "world"
    label: "Al Jazeera - All"

  - url: "https://rss.nytimes.com/services/xml/rss/nyt/MiddleEast.xml"
    outlet_slug: "nytimes"
    category: "world"
    label: "NYT Middle East"
```

### 2. feedparser for RSS parsing

Use the `feedparser` library — it's the de facto Python RSS/Atom parser, handles encoding edge cases, date normalization, and malformed feeds gracefully.

**Why not raw XML parsing:** RSS feeds have many format variations (RSS 2.0, Atom, RDF). feedparser abstracts this.

### 3. trafilatura for full-text extraction

Use `trafilatura` to fetch and extract article body text from the URL in each RSS entry.

**Why over newspaper3k:** newspaper3k is unmaintained. trafilatura is actively maintained, has better extraction quality on modern news sites, and handles metadata extraction as a bonus.

**Fallback:** If trafilatura fails (paywall, timeout, JS-only page), submit the article with `snippet` only (from RSS `<description>`) and `raw_text=None`. The ingest schema allows this — analysis quality will be lower but the article still enters the pipeline.

### 4. Submit to ingest API via HTTP

The fetcher POSTs to `POST /api/v1/ingest` rather than calling the service layer directly.

**Why HTTP over direct service call:** Keeps the fetcher fully decoupled. It can run as a separate process, Lambda, or even on a different machine. The ingest API already handles deduplication, so re-polling the same feed is safe.

### 5. Rate limiting and politeness

- **Per-feed poll interval:** Configurable, default 15 minutes. Respect RSS `<ttl>` if present.
- **Per-domain request delay:** 2-second delay between full-text fetches to the same domain (configurable).
- **User-Agent:** Set a descriptive User-Agent header for full-text fetches.

### 6. Worker execution model

Single entry point: `python -m storydiff.rss`

- **One-shot mode (default):** Poll all feeds once, submit articles, exit. Suitable for cron / Lambda.
- **Loop mode (`--loop`):** Poll feeds repeatedly on the configured interval. Suitable for long-running worker.

### 7. Outlet slug resolution for Google News

Google News RSS aggregates articles from many outlets. The RSS entry `<source>` tag contains the outlet name. The fetcher SHALL attempt to map this to a known `media_outlet_slug` via a lookup table in the feed config, falling back to a slugified version of the source name.

## Risks / Trade-offs

- **Full-text extraction quality varies** → Mitigation: trafilatura handles most news sites well. Articles where extraction fails still get ingested with snippet only.
- **Paywalled articles return truncated text** → Mitigation: Accept partial text. Analysis pipeline should handle short text gracefully. Can add a paywall-detection heuristic later.
- **Google News RSS may change or rate-limit** → Mitigation: Google News RSS has been stable for years. If it breaks, it's one feed config entry to remove.
- **Feed URLs go stale** → Mitigation: Log warnings for feeds that return errors. Operator reviews logs periodically.
- **Duplicate submissions on every poll cycle** → Mitigation: Existing dedup in ingest handles this — `duplicate_ignored` responses are expected and harmless.

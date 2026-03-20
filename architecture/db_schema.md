# Multi-Source Narrative Variance Analyzer

## Database Schema + API Specification

### Prototype v1

## 1. Scope

This document defines:

- the relational database schema for the prototype
- vector storage conventions for Qdrant
- API contracts for the backend
- event payload formats for async processing

This spec is optimized for:

- Postgres as source of truth
- Qdrant as vector DB
- LangGraph for AI workflow orchestration
- Next.js SSR frontend
- curated English-language text news sources
- topic clustering, consensus summaries, and narrative variance metrics

---

## 2. Design Principles

1. Postgres stores all primary and derived records.
2. Qdrant stores embeddings for retrieval and cluster matching.
3. Topic clustering is a first-class concept.
4. AI-derived outputs are persisted and versioned where needed.
5. APIs are read-optimized for the frontend.
6. Categories are flat, not hierarchical, in v1.
7. Reliability score represents confidence in system analysis, not article truthfulness.

---

## 3. Database Schema

---

## 3.1 `media_outlets`

Stores supported news publishers.

````sql
CREATE TABLE media_outlets (
    id BIGSERIAL PRIMARY KEY,
    slug VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255) NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


## 3.2 `categories`

Stores flat product categories.

```sql
CREATE TABLE categories (
    id BIGSERIAL PRIMARY KEY,
    slug VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL UNIQUE,
    display_order INT NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
````

**Notes:**

- No `parent_id` in prototype.
- Categories are horizontal.

---

## 3.3 `articles`

Stores ingested article metadata and lightweight text fields.

```sql
CREATE TABLE articles (
    id BIGSERIAL PRIMARY KEY,
    source_article_id VARCHAR(255),
    media_outlet_id BIGINT NOT NULL REFERENCES media_outlets(id),
    url TEXT NOT NULL,
    canonical_url TEXT NOT NULL,
    title TEXT NOT NULL,
    raw_text TEXT,
    snippet TEXT,
    language VARCHAR(20) NOT NULL DEFAULT 'en',
    published_at TIMESTAMPTZ NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_category VARCHAR(255),
    article_fingerprint VARCHAR(255) NOT NULL,
    dedupe_key VARCHAR(255) NOT NULL UNIQUE,
    processing_status VARCHAR(50) NOT NULL DEFAULT 'pending',
    category_id BIGINT REFERENCES categories(id),
    topic_id BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**Recommended enum-like values for `processing_status`:**

- `pending`
- `analyzing`
- `analyzed`
- `failed`
- `skipped`

**Notes:**

- `dedupe_key` is used for upsert/idempotency.
- `topic_id` is optional here for convenience, but the canonical linkage is via `topic_article_links`.
- `raw_text` may be null if only snippet/metadata is available.

---

## 3.4 `article_analysis`

Stores AI-derived article-level outputs.

```sql
CREATE TABLE article_analysis (
    article_id BIGINT PRIMARY KEY REFERENCES articles(id) ON DELETE CASCADE,
    summary TEXT,
    consensus_distance NUMERIC(6,4),
    framing_polarity NUMERIC(6,4),
    source_diversity_score NUMERIC(6,4),
    novel_claim_score NUMERIC(6,4),
    reliability_score NUMERIC(6,4),
    polarity_labels_json JSONB,
    model_version VARCHAR(100) NOT NULL,
    analyzed_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**Recommended score ranges:**

- `consensus_distance`: 0 to 1
- `framing_polarity`: -1 to 1 or 0 to 1 depending on model choice
- `source_diversity_score`: 0 to 1
- `novel_claim_score`: 0 to 1
- `reliability_score`: 0 to 1

**`polarity_labels_json` can include interpretable tags like:**

- `emotionally_loaded`
- `accusatory_tone`
- `neutral_formulation`
- `institutional_language`

---

## 3.5 `article_entities`

Stores extracted named entities.

```sql
CREATE TABLE article_entities (
    id BIGSERIAL PRIMARY KEY,
    article_id BIGINT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    entity_text TEXT NOT NULL,
    normalized_entity TEXT,
    entity_type VARCHAR(100),
    salience_score NUMERIC(6,4),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**Example values for `entity_type`:**

- `PERSON`
- `ORG`
- `GPE`
- `EVENT`
- `LAW`
- `PRODUCT`

---

## 3.6 `topics`

Stores current state of topic clusters.

```sql
CREATE TABLE topics (
    id BIGSERIAL PRIMARY KEY,
    category_id BIGINT NOT NULL REFERENCES categories(id),
    canonical_label TEXT NOT NULL,
    current_title TEXT NOT NULL,
    current_summary TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    first_seen_at TIMESTAMPTZ NOT NULL,
    last_seen_at TIMESTAMPTZ NOT NULL,
    article_count INT NOT NULL DEFAULT 0,
    source_count INT NOT NULL DEFAULT 0,
    current_reliability_score NUMERIC(6,4),
    current_consensus_version INT NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**Recommended values for `status`:**

- `active`
- `cooling`
- `archived`
- `merged`

**Notes:**

- `canonical_label` is an internal stable identifier-like text label.
- `current_title` is display-friendly.
- `current_summary` is the latest consensus summary.

---

## 3.7 `topic_versions`

Stores historical consensus snapshots.

```sql
CREATE TABLE topic_versions (
    id BIGSERIAL PRIMARY KEY,
    topic_id BIGINT NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    version_no INT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT,
    reliability_score NUMERIC(6,4),
    article_count INT NOT NULL,
    source_count INT NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (topic_id, version_no)
);
```

**Notes:**

- Enables timeline view and diffing of consensus evolution.

---

## 3.8 `topic_article_links`

Canonical topic membership table.

```sql
CREATE TABLE topic_article_links (
    topic_id BIGINT NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    article_id BIGINT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    assignment_confidence NUMERIC(6,4) NOT NULL,
    assignment_reason_json JSONB,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (topic_id, article_id)
);
```

**Notes:**

- `assignment_reason_json` can store model/debug reasons such as:
  - semantic similarity score
  - entity overlap count
  - temporal score
  - category match flag

---

## 3.9 `media_aggregates`

Stores publisher-level aggregated analytics across time windows.

```sql
CREATE TABLE media_aggregates (
    id BIGSERIAL PRIMARY KEY,
    media_outlet_id BIGINT NOT NULL REFERENCES media_outlets(id),
    category_id BIGINT REFERENCES categories(id),
    window_start TIMESTAMPTZ NOT NULL,
    window_end TIMESTAMPTZ NOT NULL,
    article_count INT NOT NULL DEFAULT 0,
    avg_consensus_distance NUMERIC(6,4),
    avg_framing_polarity NUMERIC(6,4),
    avg_source_diversity_score NUMERIC(6,4),
    avg_novel_claim_score NUMERIC(6,4),
    avg_reliability_score NUMERIC(6,4),
    composite_rank_score NUMERIC(6,4),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**Notes:**

- `category_id` nullable means "all categories combined".
- Use time windows like 7d / 30d in prototype.

---

## 3.10 (Optional) `api_request_logs`

Useful for observability in prototype.

```sql
CREATE TABLE api_request_logs (
    id BIGSERIAL PRIMARY KEY,
    route VARCHAR(255) NOT NULL,
    method VARCHAR(20) NOT NULL,
    status_code INT NOT NULL,
    duration_ms INT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

## 4. Recommended Indexes

```sql
CREATE INDEX idx_articles_media_outlet_id ON articles(media_outlet_id);
CREATE INDEX idx_articles_category_id ON articles(category_id);
CREATE INDEX idx_articles_topic_id ON articles(topic_id);
CREATE INDEX idx_articles_published_at ON articles(published_at DESC);
CREATE INDEX idx_articles_processing_status ON articles(processing_status);

CREATE INDEX idx_article_entities_article_id ON article_entities(article_id);
CREATE INDEX idx_article_entities_normalized_entity ON article_entities(normalized_entity);

CREATE INDEX idx_topics_category_id ON topics(category_id);
CREATE INDEX idx_topics_status ON topics(status);
CREATE INDEX idx_topics_last_seen_at ON topics(last_seen_at DESC);

CREATE INDEX idx_topic_versions_topic_id ON topic_versions(topic_id);
CREATE INDEX idx_topic_versions_generated_at ON topic_versions(generated_at DESC);

CREATE INDEX idx_topic_article_links_article_id ON topic_article_links(article_id);
CREATE INDEX idx_topic_article_links_assignment_confidence ON topic_article_links(assignment_confidence);

CREATE INDEX idx_media_aggregates_media_outlet_id ON media_aggregates(media_outlet_id);
CREATE INDEX idx_media_aggregates_category_id ON media_aggregates(category_id);
CREATE INDEX idx_media_aggregates_window_start_end ON media_aggregates(window_start, window_end);
```

---

## 5. Qdrant Collections

### 5.1 `article_embeddings`

**Purpose:**  
Stores article vectors for:

- semantic search
- candidate retrieval
- similarity comparison

**Vector source:**  
Embedding of:

- title + snippet, or
- title + normalized text, or
- title + article summary

**Payload fields:**

```json
{
  "article_id": 123,
  "media_outlet_id": 7,
  "category_id": 2,
  "topic_id": 44,
  "published_at": "2026-03-20T08:00:00Z",
  "language": "en",
  "title": "Israel and Iran exchange new threats",
  "url": "https://example.com/news/123"
}
```

---

### 5.2 `topic_embeddings`

**Purpose:**  
Stores topic vectors for:

- topic candidate lookup during article assignment
- semantic topic search

**Vector source:**  
Embedding of:

- current topic title + current summary

**Payload fields:**

```json
{
  "topic_id": 44,
  "category_id": 2,
  "status": "active",
  "last_seen_at": "2026-03-20T09:00:00Z",
  "article_count": 18,
  "source_count": 6,
  "consensus_version": 3
}
```

---

## 6. Dedupe Strategy

**Dedupe priority order:**

1. canonical URL hash
2. source article ID if available
3. fallback fingerprint:
   - normalized title
   - outlet ID
   - publish-date bucket

**Recommended `dedupe_key`:**

- `sha256(canonical_url)`
- or `sha256(source_article_id + media_outlet_id)`
- or `sha256(normalized_title + media_outlet_id + yyyy-mm-dd-hh-bucket)`

**Write pattern:**  
Use upsert on `dedupe_key`.

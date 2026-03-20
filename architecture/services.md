## Backend Service Responsibilities

### Ingestion Service

**Handles:**

- `POST /ingest`
- dedupe/upsert
- queue publish for analysis

### Analysis Service

**Consumes:**

- `article.analyze`

**Writes:**

- `article_analysis`
- `article_entities`
- `topic_article_links`
- `articles.topic_id`
- Qdrant article vector
- optional new topic record

**Emits:**

- `topic.refresh`

### Topic Refresh Service

**Consumes:**

- `topic.refresh`

**Writes:**

- `topics`
- `topic_versions`
- Qdrant topic vector

### Aggregation Service

**Computes:**

- `media_aggregates`

**Can run:**

- on schedule
- or on selected triggers

### Core API Service

**Serves:**

- feed
- topic pages
- media pages
- search
- categories

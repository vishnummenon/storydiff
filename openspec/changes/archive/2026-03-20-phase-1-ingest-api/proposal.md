## Why

Phase 1 already has Postgres (including `articles` with `dedupe_key`) and Qdrant collections, but there is no HTTP surface to accept article metadata or to drive downstream analysis. We need a bounded **ingestion** path that validates input, applies dedupe/upsert rules, persists rows, and emits async events so the analysis pipeline can start without coupling ingestion to LangGraph or Qdrant writes.

## What Changes

- Add **`POST /api/v1/ingest`** aligned with [architecture/api_contract.md](../../../architecture/api_contract.md) §8.1 (request validation, response envelope, `dedupe_status`, `processing_status`).
- Implement an **ingestion package** (`src/storydiff/ingestion/`) with thin HTTP layer and **`IngestionService`** (or equivalent) owning validation, dedupe key selection, upsert semantics, status fields, and event publishing—per [architecture/services.md](../../../architecture/services.md).
- Implement **dedupe/upsert** per [architecture/db_schema.md](../../../architecture/db_schema.md) §6 (priority order, `dedupe_key`, upsert write pattern).
- Add an **SQS producer abstraction**; after a successful transactional write, publish **`article.ingested`** and **`article.analyze`** payloads per [architecture/events.md](../../../architecture/events.md) §7.1–7.2.
- Extend **local dev**: `docker-compose` **LocalStack** for SQS, documented queue bootstrap and env (`AWS_ENDPOINT_URL`, queue URLs, region).
- Add **tests**: unit tests for dedupe/upsert helpers; API tests; optional integration test against LocalStack (publish + receive).

**Explicitly out of scope:** analysis graph execution, Qdrant article writes, topic assignment, feed/topic APIs.

## Capabilities

### New Capabilities

- `article-ingestion`: HTTP ingest contract, ingestion service (validation, dedupe key, upsert/`dedupe_status`, `processing_status`), SQS publishing for `article.ingested` and `article.analyze`, LocalStack-backed local dev and tests.

### Modified Capabilities

- _(none — relational and Qdrant baseline specs are unchanged; this change adds application behavior on top of existing schema.)_

## Impact

- **Backend Python package** (`backend/`): new `ingestion` module, FastAPI app/router wiring (if not present), settings for AWS/SQS, boto3 (or equivalent) dependency, test layout.
- **Infrastructure / dev**: `docker-compose.yml`, env examples (`AWS_ENDPOINT_URL`, `AWS_REGION`, queue URL vars), optional init script for queues.
- **Runtime**: Postgres writes only; no Qdrant or analysis workers in this change beyond publishing messages.

## Context

The backend currently exposes SQLAlchemy models for `articles`, `media_outlets`, and related tables ([`backend/src/storydiff/db/models.py`](../../../backend/src/storydiff/db/models.py)) but has no FastAPI application or ingest route. Phase 1 data-plane migrations and Qdrant collection setup exist; this change adds the **ingestion bounded context**: accept metadata, resolve `media_outlet_id` from slug, compute `dedupe_key` and `article_fingerprint`, upsert into Postgres, then notify analysis via SQS.

## Goals / Non-Goals

**Goals:**

- Implement **`POST /api/v1/ingest`** matching [architecture/api_contract.md](../../../architecture/api_contract.md) §8.1 (fields, validation defaults, success envelope).
- Centralize **business rules** in a service layer; route handlers parse/serialize only.
- **Dedupe** per [architecture/db_schema.md](../../../architecture/db_schema.md) §6: priority (1) canonical URL, (2) `source_article_id` + outlet, (3) normalized title + outlet + publish-date bucket; **upsert** on `dedupe_key` with API `dedupe_status` ∈ {`inserted`, `updated`, `duplicate_ignored`}.
- **Publish** JSON messages for **`article.ingested`** and **`article.analyze`** per [architecture/events.md](../../../architecture/events.md) after commit.
- **LocalStack** in Compose for SQS; document env and queue creation.

**Non-Goals:**

- Running LangGraph, writing Qdrant article vectors, topic assignment, `topic.refresh`, or implementing the analysis consumer (beyond receiving a message in an optional integration test).

## Decisions

### 1. Package layout: `storydiff.ingestion`

Place router, Pydantic request/response models, `IngestionService`, dedupe helpers, and SQS publisher wiring under **`src/storydiff/ingestion/`** (single deployable app). Keeps ingestion rules discoverable and testable in isolation.

**Alternatives:** Flat `api/` module only — rejected because it obscures bounded context; separate microservice — rejected for Phase 1 single-app scope.

### 2. `dedupe_key` computation

Implement §6 literally:

1. **Primary:** `sha256(canonical_url)` (normalized string: trim, consistent casing policy—document as lowercase URL string before hash unless product chooses preserve-case; prefer normalization that matches duplicate detection intent).
2. **If canonical URL is unsuitable** (e.g. missing in edge cases—contract requires it, so normally unused): `sha256(f"{source_article_id}:{media_outlet_id}")` when `source_article_id` present.
3. **Fallback:** `sha256(f"{normalized_title}:{media_outlet_id}:{yyyy-mm-dd-hour-bucket}")` using `published_at` in UTC.

**Selection rule:** Use the first tier that yields a stable key for the request; document the exact normalization (whitespace collapse, NFKC for title, hour bucket definition).

**Alternatives:** Single-key-only hash — rejected; does not match architecture priority.

### 3. Upsert and `dedupe_status`

Use a single **INSERT … ON CONFLICT (`dedupe_key`) DO UPDATE** (or equivalent SQLAlchemy 2 pattern) inside one transaction.

- **`inserted`:** conflict did not fire (new row).
- **`updated`:** conflict fired and at least one ingested column changed (compare normalized values before update).
- **`duplicate_ignored`:** conflict fired and ingested payload is **semantically identical** to stored row (no write beyond possibly touching `updated_at`—prefer **no row update** to avoid churn; if DB forces `updated_at` bump, still classify as `duplicate_ignored` when business fields unchanged).

**Alternatives:** Always update on conflict — rejected; loses `duplicate_ignored` semantics from the API contract.

### 4. `article_fingerprint`

Column is NOT NULL. Set **`article_fingerprint`** to the same string as **`dedupe_key`** for v1 (both are deterministic hashes of the chosen tier inputs). Simplifies storage and debugging.

**Alternatives:** Separate fingerprint algorithm — deferred; not required for ingest-only Phase 1.

### 5. `processing_status` on ingest

New rows: **`pending`**. On **update** path when not `duplicate_ignored`: reset to **`pending`** if downstream should re-run analysis when metadata changes; keep existing status if `duplicate_ignored`. Document choice: **re-pending on meaningful update** aligns with re-emitting `article.analyze`.

**Alternatives:** Never reset — rejected when title/body change should retrigger analysis.

### 6. SQS producer abstraction

Introduce a small interface, e.g. **`EventPublisher`** / **`SqsPublisher`**, with methods `publish_article_ingested(payload)` and `publish_article_analyze(payload)` (or one method with `event_type` discriminator). Implementation uses **boto3** `SQS` client configured with `endpoint_url` from `AWS_ENDPOINT_URL` when set (LocalStack).

**Queue topology:** Two environment variables, e.g. **`SQS_ARTICLE_INGESTED_QUEUE_URL`** and **`SQS_ARTICLE_ANALYZE_QUEUE_URL`**. Local dev may use two queues or the same URL twice for smoke tests—implementation sends **two messages** (ingested then analyze) per successful insert/update (not for `duplicate_ignored` unless a future flag requires it).

**Alternatives:** SNS fan-out — deferred; FIFO single queue — acceptable later; for now two URLs match clear consumer ownership.

### 7. When to emit `article.analyze`

Emit **`article.analyze`** only when **`dedupe_status`** is **`inserted`** or **`updated`** (i.e. work may be needed). Skip for **`duplicate_ignored`** to avoid analysis storms on idempotent retries.

**Alternatives:** Always emit — rejected for duplicate_ignored.

### 8. FastAPI and dependencies

Add **FastAPI**, **uvicorn**, **pydantic** v2, **boto3** to `pyproject.toml` (exact versions per lock policy). Mount router at **`/api/v1`**. Use shared DB session dependency (new small `db/session` or reuse patterns from future app module).

### 9. Media outlet resolution

Resolve **`media_outlet_slug`** → `media_outlets.id` via DB lookup. If missing or inactive: return **`4xx`** with stable error code in envelope (align with api_contract error shape when defined).

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Dedupe tier mistakes create duplicate articles | Unit tests for each tier; golden vectors for hash inputs |
| SQS publish after commit fails → drift | Log + metrics; optional outbox later; document at-least-once consumer design |
| LocalStack vs AWS behavioral gaps | Keep publisher thin; integration test only critical path |
| `duplicate_ignored` vs DB `updated_at` | Prefer no-op UPDATE when unchanged; tests assert classification |

## Migration Plan

1. Add dependencies and ingestion module; feature-flag optional if needed (default on in dev).
2. Deploy DB unchanged (schema already exists).
3. Configure real AWS queues in staging/prod; run smoke ingest + verify messages.
4. Rollback: disable route or remove router include; no schema rollback.

## Open Questions

- **Exact URL normalization** for tier-1 hash (strip fragments? query ordering?) — finalize in implementation with tests referencing real-world duplicates.
- **4xx code** for unknown `media_outlet_slug` — pick one code (e.g. `MEDIA_OUTLET_NOT_FOUND`) and document in spec if not in api_contract yet.

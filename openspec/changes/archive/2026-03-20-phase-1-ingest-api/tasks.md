## 1. Dependencies and app shell

- [x] 1.1 Add FastAPI, uvicorn, pydantic, boto3 (and httpx if needed for tests) to `backend/pyproject.toml`; run lock/install per project convention
- [x] 1.2 Introduce FastAPI application entry (e.g. `storydiff.main` or `storydiff.api.app`) mounting an `/api/v1` router; document `uvicorn` dev command in README if missing

## 2. Ingestion package structure

- [x] 2.1 Create `src/storydiff/ingestion/` with `__init__.py`, Pydantic request/response models matching [architecture/api_contract.md](../../../architecture/api_contract.md) §8.1
- [x] 2.2 Add thin `router` for `POST /ingest` that delegates to `IngestionService`
- [x] 2.3 Wire DB session dependency and common JSON envelope helpers (success/error) consistent with api_contract

## 3. Dedupe and persistence

- [x] 3.1 Implement dedupe helpers: canonical URL hash, source_article_id + outlet, fallback title + outlet + date bucket per [architecture/db_schema.md](../../../architecture/db_schema.md) §6
- [x] 3.2 Implement `IngestionService.ingest(...)`: resolve `media_outlet_slug` → id; compute `dedupe_key` and `article_fingerprint`; upsert `articles`; classify `dedupe_status`; set `processing_status` per design
- [x] 3.3 Ensure transactional boundary: commit row(s) before publishing events

## 4. SQS publisher

- [x] 4.1 Add settings for `AWS_REGION`, `AWS_ENDPOINT_URL` (optional), `SQS_ARTICLE_INGESTED_QUEUE_URL`, `SQS_ARTICLE_ANALYZE_QUEUE_URL`
- [x] 4.2 Implement `SqsPublisher` / `EventPublisher` abstraction; serialize [architecture/events.md](../../../architecture/events.md) §7.1–7.2 payloads
- [x] 4.3 Call publisher after successful commit: always `article.ingested`; `article.analyze` only for `inserted` or `updated`

## 5. LocalStack and documentation

- [x] 5.1 Extend `docker-compose.yml` with LocalStack (SQS); expose port and persist minimal config
- [x] 5.2 Add queue bootstrap: Makefile target, shell script, or documented `awslocal` commands for both queues
- [x] 5.3 Update `backend/.env.example` and backend README with env vars and local testing steps

## 6. Tests

- [x] 6.1 Unit tests: dedupe key generation (fixtures per tier), `dedupe_status` classification (insert / update / duplicate_ignored)
- [x] 6.2 API tests: validation errors; successful ingest with mocked or test DB; assert response envelope
- [x] 6.3 Optional integration test: LocalStack or moto — send message, receive and assert JSON body shape

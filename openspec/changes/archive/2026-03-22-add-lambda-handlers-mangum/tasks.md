## 1. Dependencies

- [x] 1.1 Add `mangum>=0.17,<1` to runtime dependencies in `backend/pyproject.toml`
- [x] 1.2 Run `uv lock` to update the lockfile

## 2. Mangum API Handler

- [x] 2.1 Create `backend/src/storydiff/lambda_api.py` — import `app` from `storydiff.main`, wrap with `Mangum(app, lifespan="off")` and expose as `handler`

## 3. Analysis Worker Lambda Handler

- [x] 3.1 Create `backend/src/storydiff/analysis/lambda_handler.py` with `lambda_handler(event, context)`
- [x] 3.2 Extract `event["Records"]`, parse each record's `Body` as JSON
- [x] 3.3 Validate `event_type == "article.analyze"` and presence of `article_id` — add `messageId` to `batchItemFailures` for invalid records
- [x] 3.4 Call `process_article_analysis_swallow(article_id)` — add `messageId` to `batchItemFailures` if result has `ok: False` or an exception is raised
- [x] 3.5 Return `{"batchItemFailures": [{"itemIdentifier": messageId}, ...]}`

## 4. Topic Refresh Worker Lambda Handler

- [x] 4.1 Create `backend/src/storydiff/topic_refresh/lambda_handler.py` with `lambda_handler(event, context)`
- [x] 4.2 Extract `event["Records"]`, parse each record's `Body` as JSON
- [x] 4.3 Validate `event_type == "topic.refresh"` and presence of `topic_id` — add `messageId` to `batchItemFailures` for invalid records
- [x] 4.4 Call `process_topic_refresh_swallow(topic_id)` — add `messageId` to `batchItemFailures` if result has `ok: False` or an exception is raised
- [x] 4.5 Return `{"batchItemFailures": [{"itemIdentifier": messageId}, ...]}`

## 5. Tests

- [x] 5.1 Create `backend/tests/test_lambda_analysis_handler.py` — mock `process_article_analysis_swallow`, construct a minimal SQS event dict, assert successful record returns empty `batchItemFailures`
- [x] 5.2 Add test: `ok: False` result causes the record's `messageId` to appear in `batchItemFailures`
- [x] 5.3 Add test: invalid JSON body adds `messageId` to `batchItemFailures`
- [x] 5.4 Add test: missing `article_id` adds `messageId` to `batchItemFailures`
- [x] 5.5 Create `backend/tests/test_lambda_topic_refresh_handler.py` — same four test cases for the topic refresh handler (mock `process_topic_refresh_swallow`)

## 6. Verification

- [x] 6.1 Run `uv run pytest tests/test_lambda_analysis_handler.py tests/test_lambda_topic_refresh_handler.py` — all tests pass
- [x] 6.2 Run `uv run ruff check src/storydiff/lambda_api.py src/storydiff/analysis/lambda_handler.py src/storydiff/topic_refresh/lambda_handler.py` — no lint errors
- [x] 6.3 Confirm `python -m storydiff.analysis` and `python -m storydiff.topic_refresh` still start without errors (local dev unaffected)

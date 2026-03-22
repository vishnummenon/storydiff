## Why

StoryDiff's three backend processes (FastAPI server, analysis worker, topic refresh worker) are currently only runnable as local processes. To deploy on AWS Lambda, each needs an entry point that conforms to the Lambda invocation model — without breaking the existing local dev workflow.

## What Changes

- Add `mangum` dependency to `backend/pyproject.toml`
- New file `backend/src/storydiff/lambda_api.py` — Mangum-wrapped FastAPI handler for Lambda
- New file `backend/src/storydiff/analysis/lambda_handler.py` — SQS batch handler for the analysis worker
- New file `backend/src/storydiff/topic_refresh/lambda_handler.py` — SQS batch handler for the topic refresh worker
- Unit tests for both worker Lambda handlers using mocked processing logic
- All existing entry points (`uvicorn`, `python -m storydiff.analysis`, `python -m storydiff.topic_refresh`) remain unchanged

## Capabilities

### New Capabilities

- `lambda-api-handler`: Mangum wrapper that allows the FastAPI app to be invoked by AWS Lambda (via Function URL or API Gateway), translating HTTP events to ASGI
- `lambda-analysis-handler`: Lambda SQS event handler for the article analysis worker, implementing partial batch failure reporting
- `lambda-topic-refresh-handler`: Lambda SQS event handler for the topic refresh worker, implementing partial batch failure reporting

### Modified Capabilities

*(none — no spec-level behavior changes to existing capabilities)*

## Impact

- **backend/pyproject.toml**: adds `mangum` as a runtime dependency
- **storydiff/analysis/**: new `lambda_handler.py` alongside existing `__main__.py` and `worker.py` — no changes to graph or pipeline logic
- **storydiff/topic_refresh/**: new `lambda_handler.py` alongside existing `__main__.py` and `worker.py` — no changes to pipeline logic
- **tests/**: new unit test files for both Lambda handlers
- **No API contract changes** — behavior of all endpoints is identical; only the invocation entry point changes
- **No database or Qdrant schema changes**

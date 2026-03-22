## Context

StoryDiff's two SQS workers (`analysis`, `topic_refresh`) currently run as long-polling loops: each worker owns a `boto3` SQS client, calls `receive_message` in a `while not _stop` loop, processes one message at a time, and manually calls `delete_message` on success or leaves the message for retry on failure.

AWS Lambda with SQS event source mapping inverts this model: Lambda is invoked with a batch of pre-fetched messages in `event["Records"]`. Lambda handles the polling, concurrency scaling, and (with partial batch failure reporting enabled) selective message deletion. The processing logic itself (`process_article_analysis_swallow`, `process_topic_refresh_swallow`) is unchanged.

The FastAPI app (`storydiff/main.py`) is a standard ASGI app. Lambda cannot invoke ASGI apps directly — it passes HTTP events as dicts. Mangum is an adapter that translates between the two.

## Goals / Non-Goals

**Goals:**
- Expose a `lambda_handler` entry point for both workers, compatible with Lambda SQS event source mapping
- Expose a `handler` entry point for the FastAPI app, compatible with Lambda Function URL / API Gateway via Mangum
- Implement partial batch failure reporting in both worker handlers so a single failed message does not poison the entire batch
- Preserve all existing local dev entry points without modification

**Non-Goals:**
- No Dockerfiles, CI/CD, or Terraform in this change
- No changes to LangGraph graph logic, pipeline logic, or processing functions
- No changes to the SQS polling workers (`worker.py`) used for local dev
- No changes to the API contract or database schema

## Decisions

### D1: Thin handler files, no logic duplication

The Lambda handlers (`lambda_handler.py`) are thin adapters only. All message validation and processing logic stays in the existing `worker.py` and `pipeline.py` files. The handlers extract the message body, parse it into the expected payload dict, and call the same `process_*_swallow` functions the polling workers already use.

**Why not reuse `worker.py` directly?** The polling worker owns its own SQS client, receive loop, and delete calls — none of which apply in Lambda. Reusing it would require awkward parameterization. A thin new file is cleaner.

### D2: Partial batch failure pattern (report_batch_item_failures)

Both handlers return `{"batchItemFailures": [...]}` with the `messageId` of any record that raised an exception. This requires the SQS event source mapping to have `FunctionResponseTypes: ["ReportBatchItemFailures"]` enabled (done in the infra change). Without this, a single failure retries the entire batch.

**Why not just raise and let Lambda retry the batch?** With batch size 1 (which the infra change will configure), this doesn't matter in practice. But implementing partial batch failure makes the handlers correct for any batch size and future-proofs against batch size changes.

### D3: Mangum with lifespan="off"

The FastAPI app does not use ASGI lifespan events (no startup/shutdown handlers). Mangum's `lifespan="off"` avoids spurious warnings and is appropriate for Lambda where the container lifecycle is managed externally.

### D4: `mangum` added as a runtime dependency, not optional

Mangum is a lightweight pure-Python package (~10KB). There is no reason to make it optional — it adds no meaningful weight to the image and avoids conditional import complexity.

### D5: No shared base handler class

The two worker handlers follow the same pattern but operate on different event types and call different processing functions. A shared base class would be premature abstraction for two files. Keep them independent and readable.

## Risks / Trade-offs

**[Risk] LangGraph checkpoint pool init on cold start** → The analysis pipeline initialises a Postgres connection pool for LangGraph checkpointing on first use. Lambda cold starts will incur this cost (~1-3s) in addition to Python import time. Mitigation: provisioned concurrency can be added later if cold start latency becomes a problem.

**[Risk] `process_article_analysis_swallow` / `process_topic_refresh_swallow` swallow exceptions internally** → If the swallow functions suppress all errors and return `{"ok": False}`, the Lambda handler has no exception to catch and cannot report batch item failures. Mitigation: the handlers check the return value and treat `ok: False` as a failure, adding the `messageId` to `batchItemFailures`.

**[Risk] VisibilityTimeout mismatch** → The SQS event source mapping VisibilityTimeout must be ≥ the Lambda function timeout. This is an infra concern (handled in Change 2), but if misconfigured, messages could become visible again while still being processed. No mitigation needed in this change — noted for the infra change.

## Migration Plan

This change adds new files only. No existing files are modified (except `pyproject.toml` to add `mangum`). Deployment is handled by Change 2. No rollback complexity.

## Open Questions

*(none — all decisions resolved above)*

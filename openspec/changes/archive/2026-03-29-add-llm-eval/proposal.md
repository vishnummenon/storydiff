## Why

StoryDiff's AI pipelines (classification, entity extraction, scoring, consensus summarization) run in production with no visibility into output quality or latency, and no regression baseline. Adding observability (Netra) and offline evaluation (DeepEval) closes both gaps.

## What Changes

- Add `netra-sdk` dependency and call `Netra.init()` in the FastAPI app and both worker entry points so all LLM calls, LangGraph nodes, Qdrant queries, SQS messages, and SQLAlchemy queries are traced automatically
- Add optional `NETRA_API_KEY` setting — when absent, init is skipped so local/test environments are unaffected
- Add a `backend/tests/eval/` directory (excluded from CI) with DeepEval test suites for each LLM flow:
  - Category classification accuracy
  - Entity extraction precision/recall (LLM-as-judge)
  - Article summary faithfulness + score validity
  - Consensus summary (RAG) faithfulness, neutrality, and relevance

## Capabilities

### New Capabilities

- `llm-observability`: Netra auto-instrumentation wired into FastAPI app startup and worker entry points, controlled by `NETRA_API_KEY` env var
- `llm-evaluation`: DeepEval offline eval suite covering all four LLM flows — classify, entities, summary_scores, and consensus refresh

### Modified Capabilities

<!-- None — no existing spec-level behavior is changing -->

## Impact

- **Backend runtime**: `netra-sdk` added as a dependency; `storydiff/settings.py` gains `netra_api_key: str | None`; `storydiff/main.py` and worker `__main__` files gain a conditional `Netra.init()` call
- **Tests**: New `backend/tests/eval/` directory with `conftest.py` + four test files; never run in standard `pytest` (separate path); requires `LLM_PROVIDER` configured
- **Dependencies**: `deepeval` added as dev-only dependency
- **No API changes**: no new endpoints, no schema changes, no migration needed

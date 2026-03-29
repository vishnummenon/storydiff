## Context

StoryDiff runs four LLM flows in production: category classification, entity extraction, article summary+scores, and consensus summarization (RAG). These all execute inside LangGraph graphs driven by SQS workers. There is currently no tracing of what inputs/outputs the LLMs produce, no latency visibility, and no quality regression baseline.

Two tools fill these gaps:
- **Netra** — SaaS observability; auto-instruments LangGraph, Qdrant, FastAPI, SQLAlchemy, boto3/SQS via OpenTelemetry. User already has an API key.
- **DeepEval** — offline LLM-as-judge evaluation framework with pytest integration.

## Goals / Non-Goals

**Goals:**
- Trace all LLM calls, LangGraph nodes, Qdrant queries, SQS messages, and DB queries in Netra with zero manual span creation
- Provide an offline DeepEval test suite that can be run on-demand against the real LLM stack
- Keep all changes opt-in: no Netra key → no tracing; no eval run → no LLM cost incurred

**Non-Goals:**
- Online/continuous eval (no evaluation in the hot path)
- Evaluation of the heuristic topic assignment flow (already deterministic — covered by accuracy metrics, not DeepEval)
- Custom DeepEval LLM judge implementation (use OpenAI judge via `OPENAI_API_KEY`)
- Qdrant/embedding integration eval (requires live infra — excluded for now)

## Decisions

### 1. Netra init placement

`Netra.init(api_key=..., service_name=...)` must be called once before the first instrumented call. Three entry points need it:

| Entry point | File | When called |
|-------------|------|-------------|
| FastAPI app | `storydiff/main.py` | Module import time (top of file) |
| Analysis worker | `storydiff/analysis/worker.py` — `run_worker()` | Before SQS loop |
| Topic refresh worker | `storydiff/topic_refresh/worker.py` — `run_worker()` | Before SQS loop |

**Why at module import in main.py**: FastAPI has no explicit startup hook used here; top-of-file init is the simplest and ensures instrumentation is active before the first request.

**Alternative considered**: `@app.on_event("startup")` hook — rejected because it runs after app construction, potentially missing early instrumentation.

### 2. Settings / configuration

Rather than adding `netra_api_key` to the existing per-module `AnalysisSettings` dataclass (which is already large and analysis-specific), read `NETRA_API_KEY` directly from `os.environ` at each call site with a simple one-liner helper:

```python
# storydiff/observability.py
import os
def init_netra(service_name: str) -> None:
    key = os.environ.get("NETRA_API_KEY", "").strip() or None
    if key:
        from netra import Netra
        Netra.init(api_key=key, service_name=service_name)
```

This avoids coupling Netra to any existing settings class and keeps the import lazy (no import error if `netra-sdk` is not installed).

**Why a helper module over inline code**: three call sites, same guard logic — one function is cleaner. Lazy import means missing SDK = silent no-op (useful for test environments).

### 3. DeepEval judge LLM

DeepEval's built-in metrics (G-Eval, FaithfulnessMetric, etc.) use an LLM judge. The project supports both Ollama and OpenAI for inference, but:
- G-Eval quality degrades significantly with small local models
- Eval tests are already opt-in and not run in CI
- Users running evals are expected to have `OPENAI_API_KEY` configured

**Decision**: Use OpenAI (GPT-4o-mini default) as the DeepEval judge. Document this as a requirement for the `tests/eval/` suite. The project's `OPENAI_API_KEY` env var is reused — no new key needed.

**Alternative considered**: Wrap Ollama as a `DeepEvalBaseLLM` — feasible but adds ~50 lines of boilerplate and produces lower-quality judgements. Punted for now.

### 4. Eval test data

All test fixtures are hardcoded Python constants in each test file — no external CSV/JSONL datasets. This keeps the suite portable and reviewable in-repo.

Each fixture includes real-sounding (but synthetic) news article text of ~150–300 words to give the LLM judge enough signal to evaluate faithfulness and relevance.

### 5. Eval tests excluded from default pytest run

`pyproject.toml` already sets `testpaths = ["tests"]` which would pick up `tests/eval/`. Two options:
- Add a `pytest.ini_options` `addopts` to exclude by path
- Use a custom marker and `filterwarnings`

**Decision**: Add `--ignore=tests/eval` to `addopts` in `pyproject.toml`. Evals are run explicitly with `pytest tests/eval/`. This is the least surprising approach for a new contributor.

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| `netra-sdk` not available → import error at startup | Lazy import inside helper; if key is absent the import is never attempted |
| Netra key accidentally committed | Add `NETRA_API_KEY` to `.gitignore` pattern; it already lives in `.env` which is gitignored |
| DeepEval LLM judge costs money | Evals are never run in CI; documented as on-demand only |
| Eval test fixtures go stale | Fixtures are synthetic and stable; they test structural properties (faithfulness, no hallucination) not specific facts |
| Netra SDK version incompatibility with LangGraph | Pin `netra-sdk` to a minor version in pyproject.toml and document upgrade path |

## Migration Plan

1. Install `netra-sdk` and `deepeval` — no service restart needed until code is deployed
2. Add `NETRA_API_KEY` to `.env` — Netra init fires on next server/worker start
3. `tests/eval/` is additive — no existing tests affected
4. Rollback: remove `NETRA_API_KEY` from env → `init_netra()` becomes a no-op; remove the three `init_netra()` call sites

## Open Questions

- What Netra `service_name` values to use? Proposal: `"storydiff-api"`, `"storydiff-analysis-worker"`, `"storydiff-topic-refresh-worker"`.
- DeepEval version to pin? Latest stable (`>=2.0`) — check for LangGraph compatibility before locking a patch version.

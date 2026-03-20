## Why

Ingest already persists articles and emits `article.analyze`, but nothing consumes that queue to run the AI workflow, persist derived rows, or populate Qdrant for article-level retrieval. Phase 2 closes that gap per [architecture/build_order.md](../../../architecture/build_order.md): an async analysis service runs the article analysis graph, persists analysis outputs in Postgres (source of truth per [architecture/hld.md](../../../architecture/hld.md) §3.1), and writes article embeddings to Qdrant (§3.2, §7.2) so later phases can build on real vectors and stored entities/summaries/scores.

## What Changes

- Add an **analysis worker** (SQS-compatible consumer) that receives `article.analyze` payloads per [architecture/events.md](../../../architecture/events.md) §7.2, loads article text/metadata, and runs a **LangGraph** workflow with bounded nodes (retries/state per HLD §6).
- **Generate article embeddings** with **sentence-transformers** using model **`all-MiniLM-L6-v2`**, then **upsert** vectors into the existing `article_embeddings` collection with payload fields aligned to [architecture/hld.md](../../../architecture/hld.md) §7.2 / §8 and [architecture/db_schema.md](../../../architecture/db_schema.md) §5.1, using an **idempotent point-id strategy** (e.g. `article_id` as point id) consistent with [openspec/specs/qdrant-embeddings/spec.md](../../../openspec/specs/qdrant-embeddings/spec.md).
- **Classify category**, **extract entities**, **summarize**, and **compute article-level metrics** (consensus distance, framing, diversity, novel claim, reliability) for steps that do **not** require Phase 3 topic assignment; topic-dependent fields MAY be null or omitted until Phase 3. Text generation SHALL use a **pluggable LLM abstraction** so backends can be swapped via configuration; the **prototype default** is **Ollama** with **Llama 3.1 8B Instruct** (OpenAI-compatible local API), with **OpenAI** (or similar) as a supported alternative later without changing graph contracts.
- **Persist** `article_analysis` (1:1 with `articles`), `article_entities`, and update `articles` (`processing_status`, `category_id`, `model_version` / timestamps per schema).
- **Tests:** unit tests for persistence and Qdrant upsert helpers; worker/integration tests where practical (LocalStack + Postgres + Qdrant).

**Explicitly out of scope:** topic assignment logic, topic cluster retrieval/creation, `topic.refresh` worker, topic embeddings in Qdrant, read APIs, Next.js, search polish, aggregation/leaderboard.

## Capabilities

### New Capabilities

- `article-analysis`: Queue-driven article analysis pipeline—LangGraph orchestration, Sentence Transformers embeddings, **pluggable LLM** (Ollama + Llama 3.1 8B Instruct by default for prototype; configurable e.g. OpenAI), Postgres persistence for `article_analysis` / `article_entities` / `articles`, Qdrant upserts for `article_embeddings`, processing status lifecycle, tests.

### Modified Capabilities

- _(none — fulfills existing `qdrant-embeddings` and `postgres-relations` requirements without changing their normative text.)_

## Impact

- **Backend:** new `storydiff.analysis` (or equivalent) package—SQS consumer loop, LangGraph graph, embedding service, persistence layer, Qdrant client usage; optional CLI entrypoint `python -m storydiff.analysis.worker` (or similar).
- **Dependencies:** `langgraph`, `sentence-transformers` (+ transitive `torch` where applicable), existing boto3/Qdrant/SQLAlchemy stack; **HTTP client** for Ollama’s OpenAI-compatible API (prototype) and optional **`openai`** (or equivalent) package when switching to OpenAI—wired through one abstraction, not ad hoc in graph nodes.
- **Configuration:** `EMBEDDING_VECTOR_SIZE` MUST match `all-MiniLM-L6-v2` output (**384**); operators may need to recreate or re-provision `article_embeddings` if a mismatched dimension was used during Phase 1-only dev.
- **Infrastructure:** same LocalStack/Postgres/Qdrant as Phase 1; no new deploy target required for the prototype.

## Context

Phase 1 delivers Postgres schema, Qdrant collections, `/ingest`, and `article.analyze` queue messages. Phase 2 adds the consumer side: a long-running worker that processes each message idempotently, runs a bounded LangGraph workflow, writes derived data to Postgres, and upserts article vectors into Qdrant. [architecture/hld.md](../../../architecture/hld.md) §5.2 describes the full eventual pipeline; build order defers topic assignment and topic vectors to Phase 3.

## Goals / Non-Goals

**Goals:**

- Poll (or long-poll) the analyze queue, parse `article.analyze` JSON, and process `article_id` with clear `processing_status` transitions (`pending` → `analyzing` → `analyzed` | `failed`).
- Use LangGraph for orchestration: checkpointing/retries acceptable where they reduce duplicate side effects; prefer idempotent Qdrant upserts and upsert-by-primary-key for Postgres.
- Pin **embedding** to `sentence-transformers` **`sentence-transformers/all-MiniLM-L6-v2`** (384-dimensional vectors, cosine-friendly).
- Upsert Qdrant points with **point id = `article_id`** (unsigned integer as Qdrant accepts) for idempotent re-runs.
- Persist `article_analysis`, replace or merge `article_entities` per run (define strategy: delete-then-insert for entities for simplicity), set `articles.category_id` when classification succeeds.
- Use a **pluggable LLM client** for all text-generation steps; **prototype default:** **Ollama** running **Llama 3.1 8B Instruct** (e.g. model tag `llama3.1:8b` or `llama3.1:latest` per Ollama’s registry) via the **OpenAI-compatible** `/v1/chat/completions` endpoint (typically `http://localhost:11434/v1`). **Later / optional:** configure the same abstraction to call **OpenAI** (or another provider) by changing base URL, API key, and model id—**no changes** to LangGraph node signatures or DB schema.

**Non-Goals:**

- Topic assignment, `topic_article_links`, `topic.refresh` emissions, or writes to `topic_embeddings`.
- Production deployment topology (Lambda vs ECS); the worker is a plain Python process.
- Read APIs, aggregation, search UX.

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Embedding model | `all-MiniLM-L6-v2` via `sentence-transformers` | Matches proposal; no API key for embeddings; predictable offline dev. |
| Vector size config | Set **`EMBEDDING_VECTOR_SIZE=384`** | MiniLM L6 outputs 384 dims; must match Qdrant collection vector params. If local Qdrant was created with 1536 (placeholder), **drop/recreate** `article_embeddings` or run collection migration before testing. |
| Distance metric | Align with existing **`QDRANT_DISTANCE_METRIC`** (e.g. Cosine) | Consistent with [openspec/specs/qdrant-embeddings/spec.md](../../../openspec/specs/qdrant-embeddings/spec.md); cosine is standard for sentence-transformers. |
| LLM for classify / summarize / scores | **Abstraction** + **Ollama (Llama 3.1 8B Instruct)** as default prototype backend | Graph nodes depend on a small interface (e.g. `complete(messages) -> str` or structured JSON helpers); **reference config** points at Ollama. Swap to **OpenAI** by env: set official API base URL, `OPENAI_API_KEY`, and model name—reuse OpenAI SDK or HTTP behind the same interface. Persist provider/model in `article_analysis.model_version` (e.g. `ollama/llama3.1:8b`, `openai/gpt-4o-mini`). |
| Graph shape | Linear or lightly branching LangGraph; one node per major step (load → embed → qdrant → classify → entities → summarize → scores → persist) | HLD §6: bounded workflow, not open-ended agents. |
| Topic-dependent metrics | `consensus_distance` (and similar) MAY be **NULL** until Phase 3 provides topic context | Avoid fake numbers; optional heuristic documented in code if needed for demos. |
| Entity updates | **Delete all `article_entities` for `article_id` then insert new rows** on each successful analysis | Simpler than diffing; acceptable for v1 volume. |

**Alternatives considered:** OpenAI `text-embedding-3-*` for vectors (rejected for Phase 2 proposal in favor of ST); single monolithic script without LangGraph (rejected—user wants graph orchestration per HLD); **hard-coding OpenAI only** (rejected—Ollama keeps prototype cost at zero and data local; abstraction preserves OpenAI for higher-quality dev runs).

## LLM abstraction (prototype vs later)

- **Interface:** One module (e.g. `storydiff.analysis.llm`) exposes chat/JSON helpers used by graph nodes. Implementations: **`OllamaChatClient`** (OpenAI-compatible base URL + model name, no key) and **`OpenAIChatClient`** (or thin wrapper) selected by **`LLM_PROVIDER`** / **`OLLAMA_BASE_URL`** / **`OPENAI_API_KEY`** as documented.
- **Prototype path:** Developer runs Ollama locally, pulls Llama 3.1 8B Instruct, sets env so the worker targets `localhost:11434` (or Docker host).
- **Switch to OpenAI:** Set provider to `openai`, set key and model; nodes unchanged.
- **Tests:** Mock the interface; do not require Ollama in unit tests. Integration tests MAY use Ollama or a recorded fixture.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Torch + transformers image size / cold start | Accept for dev; document CPU inference expectations; optional `torch` CPU wheels only. |
| Qdrant dimension mismatch vs old env (1536) | Startup or pre-write validation: embedding length must equal configured size; fail fast with clear error. |
| Duplicate SQS delivery | Idempotent Qdrant upsert by point id; Postgres upserts on `article_analysis` PK; entity replace strategy. |
| Long LLM calls | Worker visibility timeout / heartbeat pattern if needed; not required for first slice. |
| Ollama not running / wrong model | Clear connection errors; document `ollama pull llama3.1:8b` (or current tag); health check optional. |

## Migration Plan

1. Set `EMBEDDING_VECTOR_SIZE=384` in `.env` and recreate `article_embeddings` if the collection was provisioned with wrong size (no production data to preserve in prototype).
2. Deploy/run worker with same Postgres and Qdrant URLs as ingest.
3. Rollback: stop worker; articles may be left `analyzing`—manual status fix or re-queue `article.analyze` if needed.

## Open Questions

- Prompt templates per node (classification vs extraction vs summarization)—fixed in implementation; keep overridable via config if useful.
- Whether to cap `raw_text` length before embedding/LLM to control cost (especially relevant when switching from Ollama to metered APIs).

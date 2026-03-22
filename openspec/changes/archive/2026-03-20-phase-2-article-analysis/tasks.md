## 1. Package layout and configuration

- [x] 1.1 Add `storydiff.analysis` package (worker entrypoint, settings: queue URL, embedding model id, **LLM provider** env: Ollama base URL + model name for Llama 3.1 8B Instruct, optional OpenAI key/model for later).
- [x] 1.2 Document `EMBEDDING_VECTOR_SIZE=384` for `all-MiniLM-L6-v2`; update `.env.example` and validate Qdrant collection dimension matches (recreate `article_embeddings` if needed for local dev).

## 2. Embedding and Qdrant

- [x] 2.1 Implement Sentence Transformers embedding service (lazy model load, 384-dim output, cosine-normalized if required by sentence-transformers defaults).
- [x] 2.2 Implement Qdrant upsert helper for `article_embeddings` using `article_id` as point id and payload per `qdrant-embeddings` spec; fail fast on dimension mismatch.
- [x] 2.3 Add unit tests for embedding shape and Qdrant payload construction.

## 3. Persistence

- [x] 3.1 Implement SQLAlchemy (or existing ORM) operations: upsert `article_analysis`, replace `article_entities` for `article_id`, update `articles` (`processing_status`, `category_id`, `updated_at`).
- [x] 3.2 Add unit tests for persistence helpers (transaction boundaries, idempotent `article_analysis` upsert).

## 4. LangGraph pipeline

- [x] 4.1 Define LangGraph graph: load article → embed → Qdrant → classify → entities → summarize/scores → persist (with explicit skips for topic-only metrics).
- [x] 4.2 Implement **LLM abstraction** (Ollama OpenAI-compatible client as default + OpenAI-backed implementation); wire graph nodes to the interface only; set `model_version` (`provider/model`) and timestamps on `article_analysis`.
- [x] 4.3 Ensure `processing_status` transitions and error handling (mark `failed` on terminal errors).

## 5. SQS consumer

- [x] 5.1 Implement long-poll loop against analyze queue (same boto3/LocalStack patterns as ingestion publisher).
- [x] 5.2 Parse `article.analyze` payload; invoke graph per message; delete/ack on success; visibility timeout handling for failures.

## 6. Integration and docs

- [x] 6.1 Add integration test (e.g. ingest → analyze message → worker processing) or dev script with LocalStack + Postgres + Qdrant.
- [x] 6.2 Document how to run the worker alongside `docker-compose` in README or `architecture/` pointer (minimal).

# Manual smoke: analysis worker

1. Start Postgres, Qdrant, LocalStack (`docker compose up -d` from repo root) and run `scripts/localstack-init-sqs.sh`.
2. Set `backend/.env` (`DATABASE_URL`, `QDRANT_URL`, queue URLs, `EMBEDDING_VECTOR_SIZE=384`, `LLM_PROVIDER=ollama`).
3. Run `uv run python -c "from storydiff.qdrant.collections import ensure_collections; ensure_collections()"` from `backend/` (recreate `article_embeddings` if dimension changed).
4. Start Ollama; `ollama pull llama3.1:8b` and `ollama pull all-minilm`.
5. `POST /api/v1/ingest` an article, then `uv run python -m storydiff.analysis` to drain `article.analyze`.

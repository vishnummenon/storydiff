# Article analysis worker

Phase 2 async consumer for `article.analyze` (SQS). Implementation lives in `backend/src/storydiff/analysis/`; runbook and environment variables are documented in [`backend/README.md`](../backend/README.md) (section **Article analysis worker**).

LangGraph state is persisted to Postgres via `langgraph-checkpoint-postgres` (see `storydiff.analysis.checkpointing`), using `thread_id` = `article-analysis-<article_id>` so a crashed run can resume from the last checkpoint on redelivery.

## Context

Phase 2 added article analysis outputs but left topic assignment and refresh incomplete. The system already uses Postgres for core entities and Qdrant for embeddings. Phase 3 must assign articles to topics during analysis, recompute topic consensus asynchronously, and compute `consensus_distance` for articles with a topic consensus.

## Goals / Non-Goals

**Goals:**
- Assign each analyzed article to a best-fit topic or create a new topic when no candidate meets threshold.
- Persist article-topic links and topic metadata changes, including `consensus_distance` when available.
- Recompute topic consensus (title/summary/reliability) and version it, then update topic embeddings in Qdrant.
- Backfill `consensus_distance` for linked articles after consensus refresh.
- Guard refresh with cooldown/thresholds and idempotent processing.

**Non-Goals:**
- Read APIs, search, or media aggregates.
- Frontend changes.
- Full production-grade clustering beyond Phase 3 requirements.

## Decisions

- **Candidate retrieval via Qdrant top-N:** Use embedding similarity to narrow candidate topics (top N) before applying multi-signal scoring. This keeps per-article work bounded while leveraging vector search.
- **Multi-signal scoring with weighted features:** Combine vector similarity, entity overlap, category match, time proximity, topic recency, and source diversity into a normalized score. This balances semantic and metadata signals and is resilient to noisy individual features.
- **Threshold-based assignment + new topic creation:** If best score is below threshold, create a new topic. This prevents forced mismatches and keeps topics coherent.
- **Consensus refresh as async worker/graph:** Use a dedicated refresh pipeline triggered by `topic.refresh` events to recompute consensus. This decouples heavy recomputation from article analysis latency.
- **Consensus versioning:** Store a monotonically increasing consensus version on topics and on article links. This enables idempotent backfill and safe reprocessing.
- **Qdrant topic embedding updates:** Write refreshed topic embeddings to Qdrant on every consensus refresh, ensuring retrieval stays aligned with latest consensus.
- **Idempotency and locking:** Use per-topic locks and cooldown windows to avoid thrash. If a refresh is already in-flight or within cooldown, skip.

## Risks / Trade-offs

- **[Risk] Over-assigning to stale topics** → Mitigation: include recency/time proximity in scoring and enforce a minimum similarity threshold.
- **[Risk] Refresh thrash under bursty ingestion** → Mitigation: cooldown thresholds, event coalescing, and idempotent refresh checks.
- **[Risk] Inconsistent consensus_distance for older links** → Mitigation: backfill task during refresh keyed by consensus version.
- **[Risk] Increased load on Qdrant** → Mitigation: keep top-N bounded and batch embedding updates where possible.

## Migration Plan

1. Add schema changes for topic consensus versioning and article-topic link fields (including `consensus_distance`).
2. Implement topic assignment in the analysis graph and ensure new links are persisted.
3. Add refresh worker/graph and event emission.
4. Backfill `consensus_distance` for existing topic links during refresh jobs.
5. Monitor and tune thresholds/cooldowns before wider rollout.

## Open Questions

- What are the initial weights and thresholds for multi-signal scoring, and where should they be configured?
- What time window should the refresh job use for selecting topic articles?
- Do we need a dedicated Qdrant collection for topics or reuse existing with a type discriminator?

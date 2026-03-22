## 1. Schema and Config

- [x] 1.1 Add/verify Postgres fields for topic consensus versioning and article-topic link `consensus_distance`
- [x] 1.2 Add configuration for topic assignment (top-N, weights, threshold) and refresh (window, cooldown, min-evidence)

## 2. Topic Assignment (Article Analysis)

- [x] 2.1 Implement Qdrant candidate retrieval against `topic_embeddings` in the analysis graph
- [x] 2.2 Implement multi-signal scoring (vector, entities, category, time, recency, source diversity) with configurable weights
- [x] 2.3 Add thresholded assignment vs. new topic creation and persist article-topic links
- [x] 2.4 Compute and store `consensus_distance` when consensus embedding exists
- [x] 2.5 Emit `topic.refresh` events on assignment or new topic creation

## 3. Topic Refresh Pipeline

- [x] 3.1 Implement refresh worker/graph to load topic articles within window
- [x] 3.2 Recompute and persist consensus fields and increment consensus version
- [x] 3.3 Upsert refreshed topic embeddings in Qdrant
- [x] 3.4 Backfill missing or stale `consensus_distance` for linked articles

## 4. Guardrails and Verification

- [x] 4.1 Add idempotency/locking and cooldown checks to avoid refresh thrash
- [x] 4.2 Add tests for assignment thresholding, refresh backfill, and idempotency guards
- [x] 4.3 Validate end-to-end flow for Phase 3 build_order items

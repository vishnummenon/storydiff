## Why

Topic clustering is currently incomplete after Phase 2: analyzed articles do not get reliably assigned to a topic, topic consensus is not refreshed when new evidence arrives, and consumers cannot use a consistent distance-to-consensus signal. This change completes Phase 3 so analysis outputs a stable topic linkage and consensus data that downstream systems can trust.

## What Changes

- Add topic assignment during article analysis using candidate retrieval from Qdrant and multi-signal scoring (vector similarity, entities, categories, time proximity, topic recency, source diversity).
- Create a new topic when no candidate meets the assignment threshold; persist topic links and update article/topic fields.
- Emit `topic.refresh` events and add a refresh worker/graph that recomputes consensus fields, versions consensus, updates topic embeddings in Qdrant, and backfills missing `consensus_distance`.
- Compute and persist `consensus_distance` for analyzed articles when consensus exists; backfill for existing linked articles after refresh.
- Add guardrails for refresh idempotency and cooldown/threshold logic to avoid thrash.

## Capabilities

### New Capabilities
- `topic-assignment`: Assign analyzed articles to an existing topic or create a new topic using multi-signal scoring and thresholds.
- `topic-refresh`: Recompute topic consensus (title/summary/reliability), version consensus, update embeddings, and backfill consensus distance.

### Modified Capabilities
- `qdrant-embeddings`: Extend embeddings support to include topic embeddings and updates on refresh.

## Impact

- Article analysis graph and persistence layer (topic link creation, consensus distance storage).
- Topic refresh graph/worker and eventing (`topic.refresh`).
- Postgres schema fields for topic consensus versioning and article/topic linkage.
- Qdrant collection usage for topic embeddings and similarity retrieval.

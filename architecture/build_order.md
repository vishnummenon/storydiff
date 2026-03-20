# Build Order

## Phase 1

- Create Postgres schema
- Create Qdrant collections
- Implement `/ingest`
- Implement dedupe/upsert

## Phase 2

- Implement article analysis graph
- Persist article analysis outputs
- Write article embeddings to Qdrant

## Phase 3

- Implement topic assignment logic
- Implement topic refresh graph
- Write topic embeddings to Qdrant

## Phase 4

- Implement read APIs
- Connect Next.js SSR frontend

## Phase 5

- Implement search
- Implement media aggregates
- Polish leaderboard and timeline

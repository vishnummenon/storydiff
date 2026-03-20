# 1. Document Purpose

This document defines the prototype-ready architecture for the Multi-Source Narrative Variance Analyzer. It translates the high-level design into an implementable system structure covering:

- System components
- Data ownership
- Processing flow
- Storage design
- API surfaces
- Event model
- AI workflow orchestration
- Deployment-oriented architecture choices

**This version is optimized for:**

- Fast prototype execution
- Management demo readiness
- Explainability
- Future extensibility
- Personal upskilling in AI systems and backend architecture

---

# 2. Architecture Goals

The prototype architecture should satisfy the following goals:

- Ingest news article metadata from curated publishers
- Process articles asynchronously using AI workflows
- Group articles into time-aware topic clusters
- Generate topic consensus summaries
- Compute article-level narrative variance metrics
- Expose read-optimized APIs for a web frontend
- Support keyword and semantic search
- Remain simple enough to build quickly while still being production-shaped

---

# 3. Architecture Principles

**3.1 Postgres is the source of truth**

All primary records, analysis outputs, scores, relationships, and versions are stored in Postgres.

**3.2 Qdrant is used for semantic retrieval, not as system of record**

Qdrant stores vector representations for similarity search and cluster matching.

**3.3 AI work is asynchronous**

All expensive extraction, clustering, summarization, and scoring flows happen outside the ingest request path.

**3.4 Topic clustering is a first-class subsystem**

Topic assignment is not just a side effect of classification; it is central to product correctness.

**3.5 Derived outputs are versioned**

Consensus summaries and selected analysis outputs should be versioned for traceability.

**3.6 Read APIs are optimized for UI needs**

The frontend should not need to compose multiple backend calls to render core pages.

---

# 4. High-Level System Components

## 4.1 Ingestion Service

Responsible for:

- Receiving article payloads
- Canonicalizing data
- Deduplicating/upserting
- Persisting article metadata
- Publishing analysis trigger events

## 4.2 Analysis Service

Consumes article analysis jobs and runs the LangGraph workflow. Responsible for:

- Entity extraction
- Category classification
- Topic candidate retrieval
- Topic assignment
- Article summarization
- Variance metric computation
- Persistence of analysis outputs
- Triggering topic refresh if required

## 4.3 Topic Refresh Service

Responsible for cluster-level recomputation.

**Tasks:**

- Refresh topic consensus title
- Refresh topic consensus summary
- Update topic embedding in Qdrant
- Update topic reliability fields
- Persist new topic version

This can be a separate worker or just a distinct LangGraph path.

## 4.4 Aggregation Service

Responsible for:

- Publisher-level metric aggregation
- Time-windowed statistics
- Category-specific metrics
- Leaderboard materialization

This should run async and not block article analysis.

## 4.5 Core API Service

Read-optimized backend for frontend consumption.

Responsible for:

- Feed APIs
- Topic detail APIs
- Media/profile APIs
- Search APIs

## 4.6 Web Application

Built in Next.js with SSR.

Responsible for:

- Landing page
- Category/topic browsing
- Topic detail pages
- Media pages
- Search pages

## 4.7 Postgres

Primary storage for:

- Articles
- Media outlets
- Categories
- Topics
- Analysis results
- Entities
- Versions
- Aggregates

## 4.8 Qdrant

Vector retrieval layer for:

- Article similarity
- Topic candidate lookup
- Semantic search

## 4.9 Queue

SQS or compatible local equivalent.

Responsible for decoupling:

- Ingest from analysis
- Article analysis from topic refresh
- Topic updates from media aggregation

---

# 5. End-to-End Processing Flow

## 5.1 Ingestion Flow

1. External source sends article payload to `/ingest`.
2. Ingestion service canonicalizes payload.
3. Dedupe/upsert runs using dedupe key.
4. Article metadata persisted in Postgres.
5. `article.ingested` event emitted.
6. `article.analyze` job pushed to queue.

> **Note**: The ingest endpoint should return quickly after persistence and queueing. No AI logic should run inline.

## 5.2 Article Analysis Flow

The analysis service consumes `article.analyze`.

**LangGraph workflow:**

1. Load article metadata and available text
2. Generate article embedding
3. Store/update embedding in Qdrant
4. Classify category
5. Extract entities
6. Retrieve candidate topic clusters from Qdrant
7. Compute topic assignment using:
   - Vector similarity
   - Entity overlap
   - Time proximity
   - Category compatibility
8. Assign article to best topic or create new topic
9. Generate article summary
10. Compute article-level metrics:
    - Consensus distance
    - Framing polarity/intensity
    - Source diversity score
    - Novel claim score
    - Reliability score
11. Persist analysis outputs in Postgres
12. Emit `topic.refresh` if topic changed materially

## 5.3 Topic Refresh Flow

The topic refresh worker consumes `topic.refresh`.

**Steps:**

1. Fetch topic articles inside active time window
2. Compute recurring points
3. Generate updated consensus title
4. Generate updated consensus summary
5. Calculate topic-level reliability indicators
6. Version the new consensus state
7. Update topic table current fields
8. Generate/update topic embedding in Qdrant

**Regeneration guardrails:**

Do **not** refresh on every tiny change.  
Refresh only when:

- Topic is newly created
- Source count crossed threshold
- Article count delta crossed threshold
- Enough time elapsed
- New article had high assignment confidence and changed topic meaningfully

## 5.4 Media Aggregation Flow

Triggered periodically or from selected topic/article updates.

**Steps:**

1. Collect analyzed articles by media outlet and time window
2. Compute aggregate metrics
3. Persist into aggregate tables
4. Refresh leaderboard views

---

# 6. Why LangGraph Still Makes Sense Here

Since you explicitly want this project to upskill your AI architecture skills, keeping LangGraph is reasonable.

Your workflow really does have a sequential dependency chain in the HLD:

- Classify
- Extract entities
- Summarize
- Refresh consensus
- Compute metrics

**Where LangGraph adds value:**

- Persistent workflow state
- Retries
- Branching
- Observability
- Clearer node-level decomposition
- Future support for re-analysis flows
- Easier experimentation with model substitutions

**Recommendation:**  
Use LangGraph, but keep the graph disciplined.  
Do **not** make it open-ended or fully autonomous.
Treat it as a stateful orchestration layer for bounded tasks.

---

# 7. Storage Architecture

## 7.1 Postgres Responsibilities

Postgres stores all primary and derived records.

**Store in Postgres:**

- Article metadata
- Topic assignments
- Article summaries
- Extracted entities
- Article-level scores
- Topic consensus title/summary
- Topic version history
- Media aggregates
- Audit timestamps
- Model version fields

## 7.2 Qdrant Responsibilities

Qdrant stores vectors and searchable payload.

**Store in Qdrant:**

- Article vectors
- Topic vectors

**Article payload fields in Qdrant**

- article_id
- media_outlet_id
- category_id
- topic_id
- published_at
- language
- title
- url

**Topic payload fields in Qdrant**

- topic_id
- category_id
- status
- last_seen_at
- article_count
- source_count
- consensus_version

---

# 8. Data Model

## 8.1 media_outlets

- id
- name
- slug
- domain
- is_active
- created_at
- updated_at

## 8.2 categories

- id
- slug
- name
- display_order
- is_active
- created_at
- updated_at

> _No `parent_id` needed for v1 because categories are horizontal._

## 8.3 articles

- id
- source_article_id _(nullable)_
- media_outlet_id
- url
- canonical_url
- title
- raw_text _(nullable)_
- snippet _(nullable)_
- language
- published_at
- ingested_at
- source_category _(nullable)_
- article_fingerprint
- dedupe_key
- processing_status
- category_id _(nullable)_
- topic_id _(nullable)_
- created_at
- updated_at

## 8.4 article_analysis

- article_id
- summary
- consensus_distance
- framing_polarity
- source_diversity_score
- novel_claim_score
- reliability_score
- polarity_labels_json
- model_version
- analyzed_at
- created_at
- updated_at

## 8.5 article_entities

- id
- article_id
- entity_text
- normalized_entity
- entity_type
- salience_score
- created_at

## 8.6 topics

- id
- category_id
- canonical_label
- current_title
- current_summary
- status
- first_seen_at
- last_seen_at
- article_count
- source_count
- current_reliability_score
- current_consensus_version
- created_at
- updated_at

## 8.7 topic_versions

- id
- topic_id
- version_no
- title
- summary
- reliability_score
- article_count
- source_count
- generated_at
- created_at

## 8.8 topic_article_links

- topic_id
- article_id
- assignment_confidence
- assignment_reason_json
- assigned_at

## 8.9 media_aggregates

- id
- media_outlet_id
- category_id _(nullable)_
- window_start
- window_end
- article_count
- avg_consensus_distance
- avg_framing_polarity
- avg_source_diversity_score
- avg_novel_claim_score
- avg_reliability_score
- composite_rank_score _(nullable)_
- created_at
- updated_at

---

# 9. Topic Assignment Design

This is the most important logic in the system.

When a new article arrives:

**Step 1:**  
Embed the article and query nearest topic vectors in Qdrant.

**Step 2:**  
Take top N topic candidates.

**Step 3:**  
Score candidates using:

- Vector similarity
- Shared entities
- Category match
- Publish time proximity
- Topic recency
- Source diversity of cluster

**Step 4:**  
If best candidate score crosses threshold, assign article to topic.

**Step 5:**  
If not, create a new topic.

**Topic vector update strategy:**  
Each time topic consensus changes, regenerate topic vector using: `current_title + current_summary`.  
That becomes the topic embedding stored in Qdrant.

> **Why not use centroid only?**  
> A centroid is useful, but embedding the consensus title/summary is easier to interpret and better aligned with the topic’s current meaning. You can add centroid logic later if needed.

---

# 10. Dedupe Strategy

Do **not** dedupe only on title + media outlet.  
Your original HLD asks about this tradeoff directly.

**Recommended dedupe order:**

1. Canonical URL hash
2. Source article ID if available
3. Fallback fingerprint:
   - Normalized title
   - Media outlet
   - Publication date bucket

**Write behavior:**  
Use upsert based on dedupe key.  
This gives idempotency and protects you against duplicate webhooks.

---

# 11. Event Model

For the prototype, keep the event model simple.

**Events**

## 11.1 article.ingested

Published after article persistence succeeds.

**Payload:**

- article_id
- media_outlet_id
- published_at
- dedupe_status

## 11.2 article.analyze

Queue message for analysis execution.

**Payload:**

- article_id

## 11.3 topic.refresh

Published when topic state should be recomputed.

**Payload:**

- topic_id
- trigger_article_id
- refresh_reason

_Optional later_: `media.aggregate.refresh`

---

# 12. API Contract

Your HLD already proposed `/feed`, `/feed/topics/{id}`, and `/media` as core surfaces.

We’ll formalize them.

## 12.1 `GET /feed`

Returns category-wise topic tiles.

**Response shape:**

- categories
  - id
  - name
  - slug
  - topics
    - id
    - title
    - article_count
    - source_count
    - updated_at
    - reliability_score

## 12.2 `GET /topics/{topicId}`

Returns topic detail page data.

Includes:

- Topic metadata
- Consensus title
- Consensus summary
- Reliability score
- Article count
- Source count
- Timeline metadata
- Source article list

Each source article includes:

- article_id
- title
- url
- media_outlet
- published_at
- article_summary
- consensus_distance
- framing_polarity
- source_diversity_score
- novel_claim_score
- reliability_score
- polarity_labels

## 12.3 `GET /media`

Returns publisher leaderboard and summary analytics.

## 12.4 `GET /media/{mediaId}`

Returns publisher detail.

Includes:

- Aggregate metrics
- By-category breakdown
- Recent topics covered

## 12.5 `GET /search`

Supports:

- Keyword search from Postgres
- Semantic search via Qdrant

**Query params:**

- `q`
- `mode=keyword|semantic|hybrid`
- `category`
- `date_range`

## 12.6 `GET /topics/{topicId}/timeline`

Returns topic version history and evolution.

---

# 13. Web Architecture

Use Next.js with SSR as decided.

**Why SSR is useful here**

Your original HLD explicitly prioritized SEO and asked whether SSR is needed.

For this product, SSR helps because:

- Category pages are content-centric
- Topic detail pages should be discoverable
- The platform is largely read-heavy
- Consensus pages can be cached well

**Rendering model:**

- Landing page: SSR + caching
- Topic pages: SSR + revalidation
- Media pages: SSR
- Search page: client + server mixed depending on query mode

**CDN:**  
Yes, use CDN for:

- Static assets
- SSR page caching where possible
- Public pages

---

# 14. Search Design

Your HLD wants both keyword and semantic search.

**Keyword search:**  
Use Postgres full-text search on:

- Article titles
- Topic titles
- Consensus summaries
- Entity names if needed

**Semantic search:**  
Use Qdrant against:

- Article vectors
- Topic vectors

**Hybrid ranking:**  
Prototype ranking can combine:

- Keyword match score
- Vector similarity
- Freshness boost

---

# 15. Reliability Score Interpretation

The reliability score should reflect confidence in the system’s analysis, **not** truthfulness of the article.

Inputs may include:

- Number of articles in topic
- Number of unique outlets in topic
- Topic recency
- Assignment confidence
- Degree of agreement across sources
- Availability of usable text

This should appear clearly in product copy and metadata.

---

# 16. Recommended LangGraph Layout

**Graph A: Article Analysis Graph**

_Nodes:_

- load_article
- generate_embedding
- classify_category
- extract_entities
- retrieve_candidate_topics
- assign_or_create_topic
- summarize_article
- compute_scores
- persist_outputs
- emit_topic_refresh_if_needed

**Graph B: Topic Refresh Graph**

_Nodes:_

- load_topic_articles
- compute_cluster_state
- generate_consensus_title
- generate_consensus_summary
- compute_topic_reliability
- persist_topic_version
- update_topic_vector

This keeps article-level and topic-level workflows cleanly separated.

---

# 17. Model Usage Strategy

To control cost and improve clarity:

**Small/fast model** (use for):

- Category classification
- Entity extraction
- Polarity labeling
- Maybe source-diversity estimation

**Better reasoning model** (use for):

- Topic disambiguation only when needed
- Consensus summary generation
- Novel claim estimation if done semantically

**Embedding model** (use for):

- Article vectors
- Topic vectors

---

# 18. Prototype Constraints

This architecture assumes:

- Curated source set
- English only
- Text articles only
- Limited categories
- Metadata-first ingestion
- AI summaries and scores stored in Postgres
- No graph layer
- No user auth/payments in v1

These align with your HLD’s declared prototype focus and out-of-scope items.

---

# 19. Recommended Build Order

**Phase 1**

- Postgres schema
- Ingest service
- Dedupe/upsert
- Queue
- Basic article table population

**Phase 2**

- Qdrant integration
- Article embeddings
- Article analysis LangGraph
- Article summaries + scores

**Phase 3**

- Topic assignment
- Topic refresh graph
- Consensus summary/versioning

**Phase 4**

- Read APIs
- Next.js SSR frontend
- Feed/topic/media pages

**Phase 5**

- Semantic search
- Media aggregation
- Leaderboard

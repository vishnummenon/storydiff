# core-read-api Specification

## Purpose

Read-only HTTP API for the StoryDiff backend: feed, topic detail, media analytics, search, and categories under `/api/v1`, aligned with [architecture/api_contract.md](../../../architecture/api_contract.md) §8.2–8.8.

## Requirements

### Requirement: Read API routes are mounted under `/api/v1`

The system SHALL expose feed, topic, timeline, media, search, and categories endpoints with paths **`/api/v1/feed`**, **`/api/v1/topics/{topicId}`**, **`/api/v1/topics/{topicId}/timeline`**, **`/api/v1/media`**, **`/api/v1/media/{mediaId}`**, **`/api/v1/search`**, and **`/api/v1/categories`**, consistent with [architecture/api_contract.md](../../../architecture/api_contract.md) §8 and [architecture/hld.md](../../../architecture/hld.md) §12.

#### Scenario: Versioned prefix matches ingest

- **WHEN** a client calls a Core Read endpoint
- **THEN** the path SHALL begin with **`/api/v1`** alongside existing **`POST /api/v1/ingest`**

### Requirement: Success and error responses use the common envelope

Successful responses SHALL return HTTP 2xx with JSON body **`data`**, **`meta`** (object, may be empty), and **`error`** null. Errors SHALL return **`data`** null and **`error`** with **`code`** and **`message`**, per [architecture/api_contract.md](../../../architecture/api_contract.md) Common Response Envelope. The implementation SHALL reuse **`storydiff.ingestion.envelope`** helpers where appropriate.

#### Scenario: Success envelope shape

- **WHEN** a read endpoint returns a successful payload
- **THEN** the response body SHALL include **`data`**, **`meta`**, and **`error`** set to null

#### Scenario: Not found returns structured error

- **WHEN** **`topicId`** or **`mediaId`** does not exist
- **THEN** the system SHALL respond with HTTP **404** and an **`error`** object including **`code`** and **`message`**

### Requirement: GET `/api/v1/feed` returns category-wise topic tiles

The system SHALL implement **`GET /api/v1/feed`** per [architecture/api_contract.md](../../../architecture/api_contract.md) §8.2. The response **`data`** SHALL include **`categories`**, each with **`id`**, **`slug`**, **`name`**, and **`topics`**. Each topic tile SHALL include **`id`**, **`title`**, optional **`summary`**, **`article_count`**, **`source_count`**, **`reliability_score`**, and **`last_updated_at`** (ISO 8601). The system SHALL support query parameters **`category`** (optional slug), **`limit_per_category`** (optional, default **10**), and **`include_empty_categories`** (optional, default **false**).

#### Scenario: Optional category filter

- **WHEN** **`category`** is provided as a category slug
- **THEN** the system SHALL restrict results to that category (or return empty topics for that filter)

### Requirement: GET `/api/v1/topics/{topicId}` returns topic detail

The system SHALL implement **`GET /api/v1/topics/{topicId}`** per [architecture/api_contract.md](../../../architecture/api_contract.md) §8.3. The **`data`** object SHALL include **`topic`** (metadata including category, **`canonical_label`**, **`title`**, **`summary`**, **`status`**, counts, reliability, timestamps, **`current_consensus_version`**) and, when **`include_articles`** is true (default), **`articles`** with nested **`media_outlet`**, **`summary`**, **`scores`** (consensus_distance, framing_polarity, source_diversity_score, novel_claim_score, reliability_score), and **`polarity_labels`** as a string array. When **`include_timeline_preview`** is true (default), **`data`** SHALL include **`timeline_preview`** listing recent versions with **`version_no`**, **`generated_at`**, and **`title`**.

#### Scenario: Unknown topic returns 404

- **WHEN** no topic exists for **`topicId`**
- **THEN** the system SHALL respond with **404** and a **`TOPIC_NOT_FOUND`** (or equivalent) error code

### Requirement: GET `/api/v1/topics/{topicId}/timeline` returns full version history

The system SHALL implement **`GET /api/v1/topics/{topicId}/timeline`** per [architecture/api_contract.md](../../../architecture/api_contract.md) §8.4. The **`data`** object SHALL include **`topic_id`** and **`versions`** ordered by **`version_no`**, each with **`title`**, **`summary`**, scores, counts, and **`generated_at`**.

#### Scenario: Unknown topic returns 404

- **WHEN** no topic exists for **`topicId`**
- **THEN** the system SHALL respond with **404** and a structured error

### Requirement: GET `/api/v1/media` returns publisher leaderboard

The system SHALL implement **`GET /api/v1/media`** per [architecture/api_contract.md](../../../architecture/api_contract.md) §8.5. The **`data`** object SHALL include **`window`**, optional **`category`**, and **`items`** with **`media_outlet`**, article counts, average scores, and **`composite_rank_score`**. The system SHALL support **`category`**, **`window`** (default **`30d`**), **`limit`** (default **50**), and **`sort_by`** as specified in the contract.

#### Scenario: Sort option honored

- **WHEN** **`sort_by`** is provided with a supported value
- **THEN** the system SHALL order **`items`** by that metric

### Requirement: GET `/api/v1/media/{mediaId}` returns publisher detail

The system SHALL implement **`GET /api/v1/media/{mediaId}`** per [architecture/api_contract.md](../../../architecture/api_contract.md) §8.6. The **`data`** object SHALL include **`media_outlet`**, **`overall_metrics`**, **`by_category`**, and **`recent_topics`**.

#### Scenario: Unknown media outlet returns 404

- **WHEN** no **`media_outlets`** row exists for **`mediaId`**
- **THEN** the system SHALL respond with **404** and a structured error

### Requirement: GET `/api/v1/search` supports keyword, semantic, and hybrid modes

The system SHALL implement **`GET /api/v1/search`** per [architecture/api_contract.md](../../../architecture/api_contract.md) §8.8. The query parameter **`q`** SHALL be required. Optional parameters SHALL include **`mode`** (`keyword` \| `semantic` \| `hybrid`), **`type`** (`topics` \| `articles` \| `all`), **`category`**, **`from`**, **`to`**, and **`limit`** (default **20**). Keyword mode SHALL query Postgres using **`tsvector`**/**`plainto_tsquery`** full-text search (not `ILIKE`). Semantic and hybrid modes SHALL use Qdrant collections configured for article and topic embeddings (see [architecture/hld.md](../../../architecture/hld.md) §12.5). The **`data`** object SHALL echo **`query`**, **`mode`**, and **`results`** with **`topics`** and **`articles`** entries including scores where applicable.

#### Scenario: Keyword-only mode does not require Qdrant

- **WHEN** **`mode`** is **`keyword`**
- **THEN** the system SHALL return matches from Postgres without requiring a successful Qdrant query

#### Scenario: Keyword mode uses full-text search

- **WHEN** **`mode`** is **`keyword`**
- **THEN** the system SHALL execute the query using **`tsvector`**/**`plainto_tsquery`** against Postgres and SHALL NOT use **`ILIKE`** pattern matching

#### Scenario: Invalid mode returns 422

- **WHEN** the **`mode`** parameter is provided with a value other than **`keyword`**, **`semantic`**, or **`hybrid`**
- **THEN** the system SHALL respond with HTTP **422** and a structured error

#### Scenario: Semantic mode without Qdrant returns 503

- **WHEN** **`mode`** is **`semantic`** or **`hybrid`** and the Qdrant service is unavailable
- **THEN** the system SHALL respond with HTTP **503** and a structured error indicating the vector store is unreachable

### Requirement: GET `/api/v1/categories` lists active categories

The system SHALL implement **`GET /api/v1/categories`** per [architecture/api_contract.md](../../../architecture/api_contract.md) §8.7. The **`data`** object SHALL include **`categories`** with **`id`**, **`slug`**, **`name`**, and **`display_order`** for active categories.

#### Scenario: Inactive categories excluded

- **WHEN** a category has **`is_active`** false
- **THEN** it SHALL NOT appear in the list

### Requirement: Read HTTP layer delegates to services

Routers SHALL NOT embed complex SQL or Qdrant client logic beyond mapping and dependency injection. Query and aggregation logic SHALL reside in **`storydiff.core_api`** service or query modules. The read API SHALL NOT import **`storydiff.analysis.graph`** or otherwise execute the LangGraph analysis pipeline.

#### Scenario: Router delegates to service

- **WHEN** a read endpoint handles a request
- **THEN** persistence reads SHALL be performed through dedicated functions or service methods, not ad hoc queries inlined in the route for non-trivial logic

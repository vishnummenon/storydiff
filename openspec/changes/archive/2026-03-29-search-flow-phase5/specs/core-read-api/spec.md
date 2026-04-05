## MODIFIED Requirements

### Requirement: GET `/api/v1/search` supports keyword, semantic, and hybrid modes
The system SHALL implement **`GET /api/v1/search`** per [architecture/api_contract.md](../../../architecture/api_contract.md) §8.8. The query parameter **`q`** SHALL be required. Optional parameters SHALL include **`mode`** (`keyword` \| `semantic` \| `hybrid`), **`type`** (`topics` \| `articles` \| `all`), **`category`**, **`from`**, **`to`**, and **`limit`** (default **20**). Keyword mode SHALL query Postgres using full-text search (`tsvector`/`plainto_tsquery`) — NOT `ILIKE` pattern matching. Semantic and hybrid modes SHALL use Qdrant collections configured for article and topic embeddings (see [architecture/hld.md](../../../architecture/hld.md) §12.5). The **`data`** object SHALL echo **`query`**, **`mode`**, and **`results`** with **`topics`** and **`articles`** entries including scores where applicable. An unsupported **`mode`** value SHALL return HTTP **422** with error code **`VALIDATION_ERROR`**. A semantic or hybrid request when Qdrant is unavailable SHALL return HTTP **503** with error code **`SEARCH_UNAVAILABLE`**.

#### Scenario: Keyword-only mode does not require Qdrant
- **WHEN** **`mode`** is **`keyword`**
- **THEN** the system SHALL return matches from Postgres without requiring a successful Qdrant query

#### Scenario: Keyword mode uses full-text search
- **WHEN** **`mode`** is **`keyword`** and **`q`** contains a word present in an article title
- **THEN** the system SHALL return that article using a `tsvector` / `@@` match, not a sequential ILIKE scan

#### Scenario: Invalid mode returns 422
- **WHEN** **`mode`** is not one of `keyword`, `semantic`, or `hybrid`
- **THEN** the system SHALL respond with HTTP **422** and `error.code` **`VALIDATION_ERROR`**

#### Scenario: Semantic mode without Qdrant returns 503
- **WHEN** **`mode`** is **`semantic`** or **`hybrid`** and the Qdrant client is not configured
- **THEN** the system SHALL respond with HTTP **503** and `error.code` **`SEARCH_UNAVAILABLE`**

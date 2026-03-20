## Requirements

### Requirement: Collections exist for article and topic vectors

The system SHALL define Qdrant collections named `article_embeddings` and `topic_embeddings` consistent with [architecture/db_schema.md](../../../architecture/db_schema.md) §5. Vector size and distance metric SHALL be explicit configuration values (for example environment variables or a documented config module). Documentation SHALL state that these values MUST match the embedding model dimensions and similarity convention used for article and topic vectors.

#### Scenario: Configurable vectors

- **WHEN** an operator sets vector dimension and distance metric in configuration
- **THEN** collection creation or validation SHALL use those values and SHALL NOT hardcode a model-specific dimension in code paths that provision collections

### Requirement: Article payload fields match the specification

For collection `article_embeddings`, stored payload keys and value types SHALL match the JSON example in [architecture/db_schema.md](../../../architecture/db_schema.md) §5.1: `article_id` (integer), `media_outlet_id` (integer), `category_id` (integer), `topic_id` (integer), `published_at` (ISO 8601 timestamp string), `language` (string), `title` (string), `url` (string).

#### Scenario: Payload contract for articles

- **WHEN** a point is written to `article_embeddings` with metadata
- **THEN** the payload SHALL use those keys with JSON value types matching the §5.1 example (integer, string, or ISO 8601 string as shown); where no value exists yet for an optional association, the implementation MAY store JSON `null` for that key but MUST NOT rename keys

### Requirement: Topic payload fields match the specification

For collection `topic_embeddings`, stored payload keys and value types SHALL match the JSON example in [architecture/db_schema.md](../../../architecture/db_schema.md) §5.2: `topic_id` (integer), `category_id` (integer), `status` (string), `last_seen_at` (ISO 8601 timestamp string), `article_count` (integer), `source_count` (integer), `consensus_version` (integer).

#### Scenario: Payload contract for topics

- **WHEN** a point is written to `topic_embeddings` with metadata
- **THEN** the payload SHALL include those keys with values of the corresponding types

### Requirement: Point identifiers enable idempotent upserts

The system SHALL document and follow a point-ID strategy in `design.md` (for example using `article_id` as the Qdrant point id for `article_embeddings` and `topic_id` for `topic_embeddings`) so upserts by domain id are idempotent without duplicating vectors.

#### Scenario: Stable identity

- **WHEN** the same logical article or topic is indexed again with updated payload or vector
- **THEN** the chosen point id strategy SHALL overwrite the same Qdrant point rather than creating a second point for the same domain id

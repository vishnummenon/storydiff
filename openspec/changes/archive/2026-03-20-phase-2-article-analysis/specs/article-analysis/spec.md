## ADDED Requirements

### Requirement: Analysis worker consumes article.analyze from SQS

The system SHALL run an asynchronous worker process that receives messages from the configured **analyze** queue (SQS-compatible, including LocalStack). Each message body SHALL be JSON containing **`event_type`** **`article.analyze`**, **`article_id`**, and **`occurred_at`**, per [architecture/events.md](../../../../../architecture/events.md) §7.2. The worker SHALL parse **`article_id`** and SHALL process that article through the analysis pipeline.

#### Scenario: Valid message starts processing

- **WHEN** a message is received with **`event_type`** **`article.analyze`** and a valid **`article_id`**
- **THEN** the worker SHALL load the article and SHALL run the analysis workflow for that id

#### Scenario: Malformed message is not silently retried forever

- **WHEN** a message body cannot be parsed or **`article_id`** is missing
- **THEN** the implementation SHALL log the error and SHALL NOT apply unbounded infinite retries without a dead-letter or discard policy

### Requirement: LangGraph orchestrates bounded article analysis

The system SHALL implement the article analysis pipeline as a **LangGraph** workflow with explicit nodes (for example load article, embed, upsert Qdrant, classify, extract entities, summarize, score, persist). The graph SHALL be bounded and deterministic (no open-ended agent loops). The implementation MAY use checkpointing or retries for resilience.

#### Scenario: Workflow is decomposed into nodes

- **WHEN** a developer inspects the analysis package
- **THEN** major steps SHALL be represented as distinct graph nodes or equivalent composable units

### Requirement: Pluggable LLM with Ollama prototype default

Text generation for **classification**, **entity extraction**, **summarization**, and **scoring** SHALL be implemented behind a **provider abstraction** (interface or injectable client) so LangGraph nodes do not call vendor SDKs or HTTP endpoints directly. The abstraction SHALL support **at least** (1) an OpenAI-compatible HTTP chat path for local **Ollama** and (2) a path for **OpenAI** (or equivalent cloud API) selectable via **configuration** (environment variables and/or documented settings) **without** changing persistence schema or graph node contracts.

For the **prototype reference configuration**, the system SHALL default to **Ollama** serving **Llama 3.1 8B Instruct** (8B instruct-class model; exact Ollama model tag MAY follow Ollama’s naming, e.g. `llama3.1:8b` or `llama3.1`, as documented in `design.md`).

#### Scenario: Prototype stack uses Ollama and Llama 3.1 8B Instruct

- **WHEN** the operator uses the documented default prototype LLM settings (no override to a cloud provider)
- **THEN** chat completion requests for analysis steps SHALL be sent via the OpenAI-compatible client to the configured Ollama base URL and **Llama 3.1 8B Instruct** (or equivalent tag resolving to that family)

#### Scenario: Switch to OpenAI via configuration

- **WHEN** the operator configures the LLM provider for OpenAI (base URL, API credentials, and model id) per `design.md`
- **THEN** the same graph nodes SHALL use the shared abstraction to call OpenAI **without** changing `article_analysis` / `article_entities` table shapes

#### Scenario: Model version records provider and model

- **WHEN** analysis completes successfully
- **THEN** **`article_analysis.model_version`** SHALL identify both **provider** and **model** (e.g. `ollama/llama3.1:8b` **or** `openai/gpt-4o-mini`) for traceability across backend switches

### Requirement: Article embeddings use Sentence Transformers MiniLM

The system SHALL generate dense embeddings using **`sentence-transformers`** with model **`all-MiniLM-L6-v2`** (or the Hugging Face id **`sentence-transformers/all-MiniLM-L6-v2`**). The embedding vector length SHALL be **384** and SHALL match **`EMBEDDING_VECTOR_SIZE`** and the Qdrant collection configuration.

#### Scenario: Embedding dimension matches configuration

- **WHEN** an embedding vector is produced for upsert
- **THEN** its length SHALL equal **`EMBEDDING_VECTOR_SIZE`** and SHALL equal the configured Qdrant vector size

### Requirement: Qdrant article_embeddings upsert after embedding

After successful embedding generation, the system SHALL upsert a point into the **`article_embeddings`** collection using the payload contract in [openspec/specs/qdrant-embeddings/spec.md](../../../../specs/qdrant-embeddings/spec.md) and [architecture/db_schema.md](../../../../../architecture/db_schema.md) §5.1: **`article_id`**, **`media_outlet_id`**, **`category_id`**, **`topic_id`**, **`published_at`**, **`language`**, **`title`**, **`url`** with types as specified; optional associations MAY use JSON **`null`** for unknown keys. The point identifier SHALL follow the idempotent strategy from **Point identifiers enable idempotent upserts** in `qdrant-embeddings` (e.g. **`article_id`** as point id).

#### Scenario: Reanalysis overwrites the same point

- **WHEN** the same **`article_id`** is analyzed again
- **THEN** the Qdrant upsert SHALL update the existing point for that id and SHALL NOT create a second point for the same **`article_id`**

### Requirement: Category classification updates articles.category_id

The system SHALL assign a **category** for the article when possible and SHALL persist **`articles.category_id`** referencing **`categories.id`**. If classification cannot produce a confident assignment, the implementation MAY leave **`category_id`** unchanged or null per existing row semantics.

#### Scenario: Successful classification sets category

- **WHEN** classification returns a valid category reference
- **THEN** **`articles.category_id`** SHALL be updated to that category

### Requirement: Entities persisted to article_entities

The system SHALL extract named entities from the article text (or best available fields) and SHALL persist rows in **`article_entities`** per [architecture/db_schema.md](../../../../../architecture/db_schema.md) §3.5 with **`entity_text`**, optional **`normalized_entity`**, **`entity_type`**, and **`salience_score`** as produced by the pipeline. On re-analysis, the implementation SHALL replace prior entities for that **`article_id`** so that stored entities match the latest run.

#### Scenario: Reanalysis replaces entities

- **WHEN** analysis completes successfully for an article that already had **`article_entities`**
- **THEN** the stored set of entities SHALL reflect the new extraction only (no stale duplicates)

### Requirement: Article analysis row and scores

The system SHALL upsert a row in **`article_analysis`** for the **`article_id`** (1:1 with **`articles`**) with **`summary`**, **`model_version`**, **`analyzed_at`**, and numeric fields **`consensus_distance`**, **`framing_polarity`**, **`source_diversity_score`**, **`novel_claim_score`**, **`reliability_score`**, and **`polarity_labels_json`** as defined in [architecture/db_schema.md](../../../../../architecture/db_schema.md) §3.4. Fields that depend on Phase 3 topic context MAY be **NULL** until topic assignment exists.

#### Scenario: Analysis row exists after success

- **WHEN** analysis completes successfully
- **THEN** **`article_analysis`** SHALL contain a row **`PRIMARY KEY`** **`article_id`** with **`model_version`** and **`analyzed_at`** set

### Requirement: Processing status lifecycle on articles

The system SHALL update **`articles.processing_status`** per [architecture/db_schema.md](../../../../../architecture/db_schema.md) §3.3 recommended values: set **`analyzing`** when work begins, **`analyzed`** on full success, and **`failed`** when the pipeline fails after retries. The system SHALL update **`articles.updated_at`** when status changes.

#### Scenario: Failure marks failed

- **WHEN** the pipeline exhausts retries or hits an unrecoverable error for an article
- **THEN** **`processing_status`** SHALL be **`failed`** (or equivalent documented terminal state)

### Requirement: Phase 3 behaviors are excluded

The system SHALL NOT implement topic assignment, SHALL NOT write to **`topic_embeddings`**, SHALL NOT publish **`topic.refresh`**, and SHALL NOT require **`topic_article_links`** writes as part of this change. **`articles.topic_id`** MAY remain unset from this pipeline.

#### Scenario: No topic refresh message

- **WHEN** analysis completes successfully for an article
- **THEN** the system SHALL NOT emit **`topic.refresh`** events

### Requirement: Automated tests for persistence and Qdrant helpers

The system SHALL include unit tests for **Postgres** persistence helpers (e.g. **`article_analysis`** / **`article_entities`** / status updates) and for **Qdrant** upsert helpers (point id and payload shape). The system SHOULD include integration tests that run against LocalStack, Postgres, and Qdrant when available in CI or dev.

#### Scenario: Qdrant helper test uses contract shape

- **WHEN** tests exercise the upsert helper with a sample article
- **THEN** the payload keys SHALL match the **`qdrant-embeddings`** article payload requirement

## ADDED Requirements

### Requirement: POST /api/v1/ingest accepts and validates article metadata

The system SHALL expose **`POST /api/v1/ingest`** that accepts a JSON body equivalent to [architecture/api_contract.md](../../../../../../architecture/api_contract.md) §8.1 and SHALL validate that **`media_outlet_slug`**, **`url`**, **`canonical_url`**, **`title`**, and **`published_at`** are present. The system SHALL default **`language`** to `en` when omitted. Optional fields **`source_article_id`**, **`raw_text`**, **`snippet`**, and **`source_category`** SHALL be accepted when provided.

#### Scenario: Validation failure returns error envelope

- **WHEN** a client omits a required field (e.g. `title`)
- **THEN** the system SHALL respond with a non-2xx status and a body matching the common error envelope pattern from [architecture/api_contract.md](../../../../../../architecture/api_contract.md) §Common Response Envelope (structured `error` with `code` and `message`)

#### Scenario: Successful body shape matches contract

- **WHEN** a client sends a valid payload per §8.1
- **THEN** the system SHALL accept and process it without stripping required semantics

### Requirement: Ingest response envelope matches §8.1 success shape

On success, the system SHALL return HTTP 200 with **`data.article_id`**, **`data.dedupe_status`**, and **`data.processing_status`**, and **`error`** null, per [architecture/api_contract.md](../../../../../../architecture/api_contract.md) §8.1. The value **`dedupe_status`** SHALL be one of **`inserted`**, **`updated`**, or **`duplicate_ignored`**.

#### Scenario: Response includes pending processing for new or updated work

- **WHEN** ingestion results in `inserted` or `updated`
- **THEN** **`processing_status`** SHALL reflect pipeline state consistent with [architecture/db_schema.md](../../../../../../architecture/db_schema.md) §3.3 recommended values (e.g. **`pending`** for newly queued analysis)

### Requirement: Ingestion business rules live in a service layer

HTTP handlers SHALL NOT embed dedupe key selection, upsert policy, or event payload construction beyond mapping to/from transport types. Validation (beyond Pydantic), **`dedupe_key`** / **`article_fingerprint`** computation, **`dedupe_status`** classification, **`processing_status`** updates, and publisher calls SHALL reside in an **`IngestionService`** (or equivalent) module under **`storydiff.ingestion`**, consistent with [architecture/services.md](../../../../../../architecture/services.md) ingestion responsibilities.

#### Scenario: Router delegates to service

- **WHEN** the ingest endpoint handles a valid request
- **THEN** persistence and side effects SHALL be invoked through the ingestion service abstraction (not ad hoc queries in the route function)

### Requirement: Dedupe key follows architecture §6 priority

The system SHALL compute **`dedupe_key`** using the priority order in [architecture/db_schema.md](../../../../../../architecture/db_schema.md) §6: (1) hash of canonical URL, (2) hash of `source_article_id` + `media_outlet_id` when applicable, (3) fallback hash of normalized title + `media_outlet_id` + publish-date bucket. The system SHALL persist **`dedupe_key`** as a **UNIQUE** upsert key matching the migrated schema.

#### Scenario: Canonical URL tier used when primary

- **WHEN** a request includes `canonical_url` suitable for tier (1)
- **THEN** **`dedupe_key`** SHALL be derived from the tier-1 rule documented in the implementation (fixed normalization + hash)

### Requirement: Upsert semantics and dedupe_status

The system SHALL persist articles using an **upsert** on **`dedupe_key`** as in [architecture/db_schema.md](../../../../../../architecture/db_schema.md) §6. The system SHALL set **`dedupe_status`** to **`inserted`** for new rows, **`updated`** when an existing row is updated with changed business fields, and **`duplicate_ignored`** when the incoming payload matches the stored row such that no meaningful update occurs.

#### Scenario: Idempotent replay yields duplicate_ignored

- **WHEN** the same ingest payload is submitted twice such that no business fields change
- **THEN** the second response SHALL report **`dedupe_status`** **`duplicate_ignored`** (and SHALL NOT publish **`article.analyze`** per product rule in design)

### Requirement: article.ingested event payload

After a successful transactional write for **`inserted`**, **`updated`**, or **`duplicate_ignored`**, the system SHALL publish an **`article.ingested`** message whose JSON body matches [architecture/events.md](../../../../../../architecture/events.md) §7.1 (`event_type`, `article_id`, `media_outlet_id`, `published_at`, `dedupe_status`, `occurred_at` as ISO 8601 timestamps).

#### Scenario: Payload fields present

- **WHEN** a message is published for a persisted article
- **THEN** **`event_type`** SHALL be **`article.ingested`** and **`article_id`** SHALL match the database primary key

### Requirement: article.analyze event payload when analysis should run

When **`dedupe_status`** is **`inserted`** or **`updated`**, the system SHALL publish **`article.analyze`** with the shape in [architecture/events.md](../../../../../../architecture/events.md) §7.2 (`event_type`, `article_id`, `occurred_at`). The system SHALL NOT publish **`article.analyze`** for **`duplicate_ignored`** unless a future explicit requirement adds a flag.

#### Scenario: Analyze event after material ingest

- **WHEN** ingestion completes with **`dedupe_status`** **`inserted`**
- **THEN** the system SHALL publish **`article.analyze`** in addition to **`article.ingested`**

### Requirement: SQS publisher configuration

The system SHALL send SQS messages using configurable queue URLs (e.g. environment variables for ingested vs analyze queues) and SHALL support **`AWS_ENDPOINT_URL`** (or equivalent) for LocalStack. The system SHALL use **`AWS_REGION`** consistent with the client. Message bodies SHALL be JSON serialized.

#### Scenario: Local endpoint overrides

- **WHEN** `AWS_ENDPOINT_URL` points to LocalStack
- **THEN** published messages SHALL be delivered to that endpoint without requiring code changes beyond configuration

### Requirement: Local development and documentation

The repository SHALL extend **`docker-compose.yml`** with a **LocalStack** service for SQS. Documentation (README or companion script) SHALL describe creating the required queues and the environment variables developers must set (`AWS_ENDPOINT_URL`, region, queue URLs).

#### Scenario: Developer can run stack locally

- **WHEN** a developer follows documented steps
- **THEN** they SHALL be able to run the API and publish messages to LocalStack SQS

### Requirement: Automated tests cover dedupe and API behavior

The system SHALL include **unit tests** for dedupe key helpers and upsert/`dedupe_status` classification, **API tests** for `POST /api/v1/ingest` (validation and success paths), and **MAY** include an **integration test** that publishes to LocalStack (or moto) and receives the message to verify end-to-end publish.

#### Scenario: Regression protection for dedupe

- **WHEN** code changes alter hash or upsert logic
- **THEN** unit tests SHALL fail if **`dedupe_key`** or **`dedupe_status`** behavior regresses for fixed fixtures

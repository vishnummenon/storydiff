## ADDED Requirements

### Requirement: Netra auto-instrumentation is initialized at startup
The system SHALL initialize Netra tracing before any LLM, Qdrant, database, or SQS operation executes. Initialization SHALL be conditional on the presence of a `NETRA_API_KEY` environment variable. When the key is absent the system SHALL start normally without tracing.

#### Scenario: API server starts with NETRA_API_KEY set
- **WHEN** `NETRA_API_KEY` is present in the environment and the FastAPI app module is imported
- **THEN** `Netra.init()` is called with the key and service name `"storydiff-api"` before the first request is handled

#### Scenario: API server starts without NETRA_API_KEY
- **WHEN** `NETRA_API_KEY` is absent or empty in the environment
- **THEN** the application starts normally and no Netra initialization is attempted

#### Scenario: Analysis worker starts with NETRA_API_KEY set
- **WHEN** `NETRA_API_KEY` is present and the analysis worker's `run_worker()` is called
- **THEN** `Netra.init()` is called with service name `"storydiff-analysis-worker"` before the SQS polling loop begins

#### Scenario: Topic refresh worker starts with NETRA_API_KEY set
- **WHEN** `NETRA_API_KEY` is present and the topic refresh worker's `run_worker()` is called
- **THEN** `Netra.init()` is called with service name `"storydiff-topic-refresh-worker"` before the SQS polling loop begins

### Requirement: Observability helper encapsulates init logic
The system SHALL provide a single `init_netra(service_name: str)` helper function in `storydiff/observability.py`. This function SHALL lazily import `netra-sdk`, read `NETRA_API_KEY` from the environment, and call `Netra.init()` only when the key is present. The import SHALL be deferred so that the application starts normally even if `netra-sdk` is not installed.

#### Scenario: Helper called with key present
- **WHEN** `init_netra("storydiff-api")` is called and `NETRA_API_KEY` is non-empty
- **THEN** `Netra.init(api_key=<key>, service_name="storydiff-api")` is invoked exactly once

#### Scenario: Helper called without key
- **WHEN** `init_netra("storydiff-api")` is called and `NETRA_API_KEY` is absent
- **THEN** no import of `netra-sdk` is attempted and no exception is raised

### Requirement: NETRA_API_KEY is documented in the environment template
The `backend/.env.example` file SHALL include a commented-out `NETRA_API_KEY=` entry so developers know to configure it for observability.

#### Scenario: Developer copies .env.example
- **WHEN** a developer copies `.env.example` to `.env`
- **THEN** they see `NETRA_API_KEY=` as an optional configuration entry with a comment indicating it enables Netra tracing

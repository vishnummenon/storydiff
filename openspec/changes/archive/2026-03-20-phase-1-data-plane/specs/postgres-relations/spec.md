## ADDED Requirements

### Requirement: Relational schema matches prototype v1

The system SHALL provide a PostgreSQL schema equivalent to [architecture/db_schema.md](../../../../../architecture/db_schema.md) §3 for: `media_outlets`, `categories`, `articles`, `article_analysis`, `article_entities`, `topics`, `topic_versions`, `topic_article_links`, `media_aggregates`, and `api_request_logs`, including column types, nullability, defaults, uniqueness, primary keys, and foreign keys with `ON DELETE CASCADE` where the architecture SQL specifies it.

#### Scenario: Article dedupe and analysis linkage

- **WHEN** a developer inspects the `articles` and `article_analysis` definitions
- **THEN** `articles.dedupe_key` SHALL be unique and `article_analysis.article_id` SHALL reference `articles(id)` with `ON DELETE CASCADE` and SHALL enforce at most one analysis row per article (1:1)

#### Scenario: Topic membership and optional article topic pointer

- **WHEN** a developer inspects `topic_article_links` and `articles`
- **THEN** `topic_article_links` SHALL use the composite primary key `(topic_id, article_id)` with foreign keys and cascades as in the architecture doc and `articles.topic_id` SHALL remain without a foreign key to `topics` unless a separate product decision changes that

### Requirement: Recommended indexes are applied

The system SHALL create all indexes listed in [architecture/db_schema.md](../../../../../architecture/db_schema.md) §4 with the same columns and ordering (including `DESC` where specified).

#### Scenario: Index coverage for query paths

- **WHEN** migrations are applied to an empty database
- **THEN** each index name and definition in §4 SHALL exist on the corresponding table

### Requirement: Migrations are managed with Alembic

The system SHALL use Alembic for schema evolution. Initial migration(s) SHALL create the full Phase 1 relational schema from an empty database. The project SHALL document how to run `upgrade` and `downgrade` in development. The database connection URL SHALL be supplied via environment (or equivalent non-committed configuration) and SHALL NOT contain committed secrets.

#### Scenario: Clean install

- **WHEN** a developer runs Alembic upgrade against an empty Postgres database configured via environment
- **THEN** all tables and indexes from this capability SHALL be created successfully

### Requirement: SQLAlchemy definitions mirror the migrated schema

The system SHALL define SQLAlchemy models or Core table objects that match the migrated relational schema so application code can import a single package and rely on consistent naming and types. The stack SHALL use SQLAlchemy for persistence access and SHALL NOT introduce an alternate ORM or a different migration tool for this schema.

#### Scenario: Importable data layer

- **WHEN** application code imports the shared persistence package
- **THEN** it SHALL be able to use the declared SQLAlchemy mappings aligned with the Alembic revision(s) for Phase 1 tables

# search Specification

## Purpose

Full-text and semantic search capability for StoryDiff: FTS implementation requirements, category/date filter requirements, and frontend filter requirements for the `GET /api/v1/search` endpoint.

## Requirements

### Requirement: Keyword search uses Postgres full-text search via tsvector

The system SHALL implement keyword-mode search using Postgres **`tsvector`** columns and **`plainto_tsquery`** queries. The system SHALL NOT use **`ILIKE`** or other pattern-matching approaches for keyword search. Relevant tables (e.g., `articles`, `topics`) SHALL expose indexed **`tsvector`** columns to support efficient FTS queries, consistent with [architecture/db_schema.md](../../../architecture/db_schema.md).

#### Scenario: FTS query executes against tsvector column

- **WHEN** a keyword search request is received with parameter **`q`**
- **THEN** the system SHALL issue a Postgres query using **`plainto_tsquery`** against a **`tsvector`**-indexed column and SHALL NOT construct an `ILIKE '%…%'` predicate

#### Scenario: FTS index is present on searchable columns

- **WHEN** the database schema is migrated
- **THEN** a GIN index SHALL exist on the **`tsvector`** column(s) used by the keyword search path to ensure acceptable query performance

### Requirement: Search supports category and date range filters

The system SHALL support optional **`category`** (slug string), **`from`** (ISO 8601 date), and **`to`** (ISO 8601 date) query parameters on **`GET /api/v1/search`**. When provided, these filters SHALL be applied as additional predicates (AND logic) narrowing the result set, consistent with [architecture/api_contract.md](../../../architecture/api_contract.md) §8.8.

#### Scenario: Category filter restricts results to matching category

- **WHEN** the **`category`** query parameter is provided
- **THEN** the system SHALL return only topics and articles belonging to that category slug and SHALL exclude results from other categories

#### Scenario: Date range filter restricts results by publish date

- **WHEN** **`from`** and/or **`to`** query parameters are provided
- **THEN** the system SHALL include only articles whose **`published_at`** falls within the specified range (inclusive)

#### Scenario: Invalid date format returns 422

- **WHEN** **`from`** or **`to`** is provided with a value that is not a valid ISO 8601 date
- **THEN** the system SHALL respond with HTTP **422** and a structured error

#### Scenario: Filters are combinable

- **WHEN** multiple filter parameters (**`category`**, **`from`**, **`to`**) are provided simultaneously
- **THEN** the system SHALL apply all filters as conjunctive (AND) predicates and return only results satisfying all constraints

### Requirement: Frontend exposes category and date filter controls for search

The Next.js frontend SHALL provide UI controls allowing users to filter search results by **category** (dropdown or pill selector) and **date range** (from/to date inputs). Filter state SHALL be reflected in the URL query string so that filtered searches are shareable and bookmarkable, consistent with [architecture/hld.md](../../../architecture/hld.md) §12.

#### Scenario: Category filter control updates search results

- **WHEN** a user selects a category filter in the search UI
- **THEN** the frontend SHALL append the **`category`** parameter to the search request and re-render results scoped to that category

#### Scenario: Date range filter control updates search results

- **WHEN** a user sets a **`from`** or **`to`** date in the search UI
- **THEN** the frontend SHALL append the corresponding date parameter(s) to the search request and re-render results within that date range

#### Scenario: Filter state is persisted in URL

- **WHEN** any filter is applied
- **THEN** the URL query string SHALL be updated to reflect the current filter values so the filtered view can be shared or bookmarked

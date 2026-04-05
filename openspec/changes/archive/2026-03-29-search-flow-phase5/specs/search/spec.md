## ADDED Requirements

### Requirement: Keyword search uses Postgres full-text search
The system SHALL search articles and topics using Postgres `tsvector`/`tsquery` rather than `ILIKE` pattern matching. A `GENERATED ALWAYS AS … STORED` `tsvector` column SHALL exist on `articles` (covering `title`) and on `topics` (covering `current_title` and `current_summary`), each with a GIN index. The keyword search path SHALL use `plainto_tsquery('english', q)` with the `@@` operator.

#### Scenario: Keyword search matches article title
- **WHEN** a keyword query matches a word in an article's `title`
- **THEN** that article SHALL appear in the `results.articles` list

#### Scenario: Keyword search matches topic title or summary
- **WHEN** a keyword query matches a word in a topic's `current_title` or `current_summary`
- **THEN** that topic SHALL appear in the `results.topics` list

#### Scenario: Non-matching query returns empty results
- **WHEN** a keyword query matches no stored article titles or topic titles/summaries
- **THEN** `results.topics` and `results.articles` SHALL both be empty lists

### Requirement: Keyword search supports category filter
The system SHALL accept an optional `category` query parameter (slug). When provided, keyword results SHALL be restricted to articles and topics belonging to that category.

#### Scenario: Category filter excludes non-matching records
- **WHEN** a keyword query is issued with a `category` slug that does not match the article's category
- **THEN** that article SHALL NOT appear in `results.articles`

#### Scenario: Category filter restricts topic results
- **WHEN** a keyword query is issued with a `category` slug that does not match the topic's category
- **THEN** that topic SHALL NOT appear in `results.topics`

### Requirement: Keyword search supports date-range filter
The system SHALL accept optional `from` and `to` ISO datetime parameters. When provided, keyword article results SHALL be restricted to articles with `published_at` within the range. Topic results SHALL be filtered by `last_seen_at`.

#### Scenario: Date range excludes out-of-window articles
- **WHEN** a keyword query is issued with `from` and `to` that do not include the article's `published_at`
- **THEN** that article SHALL NOT appear in `results.articles`

### Requirement: Invalid search mode returns 422
The system SHALL reject requests where `mode` is not one of `keyword`, `semantic`, or `hybrid` with HTTP 422 and error code `VALIDATION_ERROR`.

#### Scenario: Unsupported mode rejected
- **WHEN** `mode` is set to an unrecognized value
- **THEN** the system SHALL respond with HTTP **422** and `error.code` equal to `VALIDATION_ERROR`

### Requirement: Semantic and hybrid search without Qdrant returns 503
When `mode` is `semantic` or `hybrid` and the Qdrant client is unavailable (not configured), the system SHALL respond with HTTP 503 and error code `SEARCH_UNAVAILABLE`.

#### Scenario: Semantic mode without Qdrant
- **WHEN** `mode` is `semantic` and no Qdrant client is configured
- **THEN** the system SHALL respond with HTTP **503** and `error.code` equal to `SEARCH_UNAVAILABLE`

### Requirement: Search frontend exposes category and date-range filters
The `/search` page SHALL render a category dropdown (populated from the active categories list) and `from`/`to` date inputs alongside the existing mode and result-type selectors. All active filters SHALL be reflected in the page URL so the search state is bookmarkable and restores correctly on reload.

#### Scenario: Category filter included in API call
- **WHEN** the user selects a category and submits the search form
- **THEN** the `category` parameter SHALL be included in the API request

#### Scenario: Date filters included in API call
- **WHEN** the user fills in a `from` or `to` date and submits
- **THEN** the corresponding parameter(s) SHALL be included in the API request

#### Scenario: Filter state persisted in URL
- **WHEN** a search is executed with category or date filters set
- **THEN** the page URL SHALL include `category`, `from`, and/or `to` query parameters

## ADDED Requirements

### Requirement: Backend CI runs on every push and PR touching backend code
The system SHALL run a GitHub Actions workflow (`backend-ci.yml`) triggered on push or pull_request targeting `main` or `dev` when any file under `backend/` changes.

#### Scenario: CI triggers on backend file change
- **WHEN** a commit is pushed that modifies a file under `backend/`
- **THEN** the backend-ci workflow starts automatically

#### Scenario: CI does not trigger on frontend-only changes
- **WHEN** a commit only modifies files under `web/`
- **THEN** the backend-ci workflow does not run

### Requirement: Backend CI runs ruff lint check
The system SHALL run `uv run ruff check` as part of the CI workflow and fail the workflow if any lint errors are found.

#### Scenario: Lint failure blocks CI
- **WHEN** ruff finds a lint error in backend source
- **THEN** the CI job exits with a non-zero code and is marked failed

### Requirement: Backend CI runs pytest against a real Postgres database
The system SHALL run `uv run pytest` with a `postgres:16` service container and set `TEST_DATABASE_URL` pointing to it. Tests that require database access MUST use this connection.

#### Scenario: Tests pass with Postgres service
- **WHEN** all tests pass against the Postgres service container
- **THEN** the CI job exits successfully

#### Scenario: Test failure blocks CI
- **WHEN** any test fails
- **THEN** the CI job exits with a non-zero code and is marked failed

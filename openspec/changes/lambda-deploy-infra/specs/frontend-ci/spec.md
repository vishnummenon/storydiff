## ADDED Requirements

### Requirement: Frontend CI runs on every push and PR touching frontend code
The system SHALL run a GitHub Actions workflow (`frontend-ci.yml`) triggered on push or pull_request targeting `main` or `dev` when any file under `web/` changes.

#### Scenario: CI triggers on frontend file change
- **WHEN** a commit is pushed that modifies a file under `web/`
- **THEN** the frontend-ci workflow starts automatically

#### Scenario: CI does not trigger on backend-only changes
- **WHEN** a commit only modifies files under `backend/`
- **THEN** the frontend-ci workflow does not run

### Requirement: Frontend CI runs lint and build
The system SHALL run `npm run lint` and `npm run build` using Node 20. Both MUST pass for the workflow to succeed.

#### Scenario: Lint failure blocks CI
- **WHEN** `npm run lint` exits with a non-zero code
- **THEN** the CI job is marked failed

#### Scenario: Build failure blocks CI
- **WHEN** `npm run build` exits with a non-zero code
- **THEN** the CI job is marked failed

#### Scenario: Successful lint and build marks CI green
- **WHEN** both lint and build complete with exit code 0
- **THEN** the CI job is marked successful

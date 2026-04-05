## ADDED Requirements

### Requirement: Three Lambda-compatible Docker images exist for the backend
The system SHALL provide three Dockerfiles (`Dockerfile.api`, `Dockerfile.analysis`, `Dockerfile.topic_refresh`) in `backend/`, each producing an image compatible with AWS Lambda container runtime using `public.ecr.aws/lambda/python:3.11` as the base.

#### Scenario: API image handler resolves correctly
- **WHEN** the API image is built and the Lambda runtime invokes it
- **THEN** the CMD resolves to `storydiff.lambda_api.handler`

#### Scenario: Analysis worker image handler resolves correctly
- **WHEN** the analysis image is built and the Lambda runtime invokes it
- **THEN** the CMD resolves to `storydiff.analysis.lambda_handler.lambda_handler`

#### Scenario: Topic refresh worker image handler resolves correctly
- **WHEN** the topic refresh image is built and the Lambda runtime invokes it
- **THEN** the CMD resolves to `storydiff.topic_refresh.lambda_handler.lambda_handler`

### Requirement: Dependencies are installed into the Lambda task root
The system SHALL install all runtime dependencies (from `pyproject.toml`, no dev deps) into `${LAMBDA_TASK_ROOT}` so that Lambda's Python runtime can import them without a virtualenv.

#### Scenario: Packages importable from Lambda task root
- **WHEN** the container starts
- **THEN** `import storydiff`, `import fastapi`, `import langgraph`, `import mangum` all succeed without activating a virtualenv

### Requirement: Images are tagged with the git commit SHA
The system SHALL tag all pushed ECR images with the full git commit SHA so that each deployment is traceable to a specific commit.

#### Scenario: Image tag matches commit
- **WHEN** an image is pushed to ECR during a deploy
- **THEN** the image tag equals the `GITHUB_SHA` of the triggering commit

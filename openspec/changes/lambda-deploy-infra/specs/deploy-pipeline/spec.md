## ADDED Requirements

### Requirement: Deploy workflow triggers only on push to main
The system SHALL run the deploy workflow (`deploy.yml`) only on push events to the `main` branch. It MUST NOT trigger on PRs or pushes to other branches.

#### Scenario: Deploy triggers on main push
- **WHEN** a commit is pushed to `main`
- **THEN** the deploy workflow starts

#### Scenario: Deploy does not trigger on PR
- **WHEN** a pull request is opened or updated
- **THEN** the deploy workflow does not run

### Requirement: Deploy workflow builds and pushes all three images to ECR
The system SHALL build `Dockerfile.api`, `Dockerfile.analysis`, and `Dockerfile.topic_refresh`, tag each with the commit SHA, and push them to their respective ECR repositories.

#### Scenario: All three images pushed on deploy
- **WHEN** the deploy workflow runs successfully
- **THEN** three new image tags (matching the commit SHA) exist in ECR — one per repository

### Requirement: Alembic migrations run before Lambda function code is updated
The system SHALL invoke the currently-deployed API Lambda with `{"action": "migrate"}` before updating any Lambda function code, and MUST wait for the invocation to complete successfully before proceeding.

#### Scenario: Migration runs before code swap
- **WHEN** the deploy workflow runs
- **THEN** `aws lambda invoke` with `{"action": "migrate"}` completes successfully before `update-function-code` is called on any function

#### Scenario: Migration failure halts deploy
- **WHEN** the migration Lambda invocation returns a non-zero status or function error
- **THEN** the deploy workflow fails and no Lambda function code is updated

### Requirement: Lambda functions are updated sequentially and waited on
The system SHALL call `aws lambda update-function-code` for each of the three functions and wait for each update to reach `Active` state before proceeding to the next.

#### Scenario: Functions updated in order
- **WHEN** the deploy workflow runs
- **THEN** the API function is updated and active, then analysis worker, then topic refresh worker

### Requirement: API Lambda handler detects and executes migration events
The system SHALL extend `storydiff/lambda_api.py` so that when the Lambda runtime invokes it with `{"action": "migrate"}` (a non-HTTP payload), it runs `alembic upgrade head` and returns `{"migrated": true}` instead of passing the event to Mangum.

#### Scenario: Migration event triggers alembic
- **WHEN** the Lambda is invoked with `{"action": "migrate"}`
- **THEN** `alembic upgrade head` runs and the function returns `{"migrated": true}`

#### Scenario: Normal HTTP events are unaffected
- **WHEN** the Lambda is invoked with a standard HTTP event (has `"requestContext"` key)
- **THEN** the event is passed to the Mangum handler as normal

### Requirement: Required GitHub secrets are documented
The system SHALL document in `README.md` the four GitHub repository secrets that must be configured before the deploy workflow can run: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `ECR_REGISTRY`.

#### Scenario: Secrets documented in README
- **WHEN** a developer reads the Deployment section of README.md
- **THEN** they can identify all required GitHub secrets and their purpose

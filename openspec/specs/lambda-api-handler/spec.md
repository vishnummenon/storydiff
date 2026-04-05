## ADDED Requirements

### Requirement: FastAPI app is invocable as a Lambda handler
The system SHALL expose the FastAPI application as an AWS Lambda handler via the Mangum ASGI adapter, so that Lambda (invoked via Function URL or API Gateway HTTP API) can serve all existing API endpoints without modification.

#### Scenario: Health check via Lambda invocation
- **WHEN** Lambda receives an HTTP GET event for `/health`
- **THEN** the handler returns a 200 response with body `{"status": "ok"}`

#### Scenario: All existing routes remain reachable
- **WHEN** Lambda receives an HTTP event for any existing API route (e.g. `POST /api/v1/ingest`, `GET /api/v1/feed`)
- **THEN** the handler returns the same response as the uvicorn-served app for the same request

#### Scenario: Local dev entry point is unaffected
- **WHEN** the app is started with `uvicorn storydiff.main:app`
- **THEN** it runs identically to before this change — `storydiff.lambda_api` is never imported in this path

### Requirement: Mangum adapter is configured with lifespan disabled
The system SHALL initialise the Mangum adapter with `lifespan="off"` because the FastAPI app does not use ASGI lifespan events.

#### Scenario: No lifespan warnings on invocation
- **WHEN** the Lambda handler is invoked
- **THEN** no lifespan-related warnings or errors appear in CloudWatch logs

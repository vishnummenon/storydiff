## Why

The Lambda handler entry points exist (Change 1), but there is no way to build, containerise, or deploy them. This change adds the full build and deployment pipeline: Docker images, GitHub Actions CI/CD, and Terraform-managed AWS infrastructure so that every push to `main` automatically delivers a tested, running system.

## What Changes

- New `backend/Dockerfile.api` — Lambda-compatible container image for the FastAPI handler
- New `backend/Dockerfile.analysis` — Lambda-compatible container image for the analysis worker
- New `backend/Dockerfile.topic_refresh` — Lambda-compatible container image for the topic refresh worker
- New `.github/workflows/backend-ci.yml` — runs ruff + pytest on every backend push/PR
- New `.github/workflows/frontend-ci.yml` — runs lint + build on every frontend push/PR
- New `.github/workflows/deploy.yml` — builds images, runs migrations, deploys to Lambda on push to `main`
- New `infra/` directory with Terraform files provisioning all AWS resources (ECR, Lambda, SQS, IAM, SSM)
- Updated `README.md` with a `## Deployment` section documenting bootstrap steps and ongoing workflow

## Capabilities

### New Capabilities

- `docker-images`: Three Lambda-compatible Docker images built from a shared dependency layer, each with a different CMD entry point
- `backend-ci`: GitHub Actions workflow that lints and tests the backend on every push/PR
- `frontend-ci`: GitHub Actions workflow that lints and builds the frontend on every push/PR
- `deploy-pipeline`: GitHub Actions deploy workflow — builds images, runs Alembic migrations via Lambda invoke, updates all three Lambda functions
- `aws-infra`: Terraform configuration for ECR repos, Lambda functions, SQS queues and DLQs, event source mappings, IAM roles, SSM parameters

### Modified Capabilities

*(none — no existing spec-level behavior changes)*

## Impact

- **backend/**: three new Dockerfiles
- **.github/workflows/**: three new workflow YAML files
- **infra/**: new directory, ~8 Terraform files
- **README.md**: new Deployment section
- **No application code changes** — existing routes, workers, and local dev workflow are unaffected
- **AWS account required** — Terraform targets real AWS resources; local dev continues to use Docker Compose + LocalStack

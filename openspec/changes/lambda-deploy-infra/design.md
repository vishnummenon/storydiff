## Context

Three Lambda entry points now exist in the backend (Mangum API handler, analysis worker handler, topic refresh worker handler). The local dev stack uses Docker Compose + LocalStack. There is no CI, no Docker build, and no AWS infrastructure. This change wires everything together: containers, pipelines, and cloud resources.

Production constraints:
- Database: Supabase PostgreSQL (free, external — not provisioned by Terraform)
- Vector DB: Qdrant Cloud (free, external — not provisioned by Terraform)
- LLM: OpenAI API (external)
- Container registry: ECR (required for Lambda container images)
- Frontend: Vercel (auto-deploys from GitHub, no Terraform or workflow needed)

## Goals / Non-Goals

**Goals:**
- Reproducible Docker images for all three Lambda functions
- Automated CI on every push/PR (tests must pass before deploy)
- Automated deploy to Lambda on every push to `main`
- All AWS resources defined in code (Terraform), version-controlled and reproducible
- Alembic migrations run automatically in the deploy pipeline before Lambda functions are updated
- Secrets stored in SSM Parameter Store, never in code or environment files

**Non-Goals:**
- Vercel configuration (manual one-time setup, documented in README)
- Supabase and Qdrant Cloud account setup (external, manual)
- Multi-environment (staging/prod) setup — single environment for now
- Blue/green or canary deployments
- Custom domain or API Gateway — Lambda Function URL is sufficient
- Monitoring or alerting setup

## Decisions

### D1: One Dockerfile per Lambda function, shared dependency install stage

All three functions share the same `pyproject.toml`. A multi-stage Docker build would save build time but adds complexity. For a personal project with three functions, three separate Dockerfiles each doing the same `uv sync` step is simpler and equally correct. The ECR layer cache means the dependency layer is only re-uploaded when deps change.

**Base image:** `public.ecr.aws/lambda/python:3.11` (official Lambda base). A `python:3.11-slim` + Lambda RIC would reduce base image size by ~500MB, but total image size is dominated by Python deps (~1GB), so the saving is marginal (~$0.15/month in ECR). Stick with the official base for reliability.

**uv install approach:** Install `uv` into the build stage, run `uv sync --no-dev`, then copy site-packages into `${LAMBDA_TASK_ROOT}`. This avoids shipping uv or a virtualenv into the final image — only the installed packages land in the Lambda root.

### D2: Alembic migrations via a dedicated Lambda invocation in the deploy pipeline

Options considered:
1. **Run alembic in the deploy workflow directly** — requires the CI runner to have a direct database connection (Supabase connection string as a secret). Simple but couples the runner to the database network.
2. **Separate migration Lambda** — clean separation but another function to manage.
3. **Invoke the API Lambda with a special `__migrate` event before updating the function code** — the Lambda handler checks for this event type, runs `alembic upgrade head`, and returns. This reuses the existing image that already has alembic installed and the database connection via SSM. **Chosen approach.**

The API Lambda's `lambda_api.py` handler will be extended to detect a `{"action": "migrate"}` event (non-HTTP event) and run migrations, then return `{"migrated": true}`. The deploy workflow invokes this synchronously before swapping the image.

### D3: Terraform S3 backend for state

Terraform state stored locally is lost if the machine changes. S3 is the simplest durable remote backend. The S3 bucket must be created manually before `terraform init` (chicken-and-egg: Terraform can't create the bucket it needs to store its own state). This one-time bootstrap step is documented in the README.

**DynamoDB state locking is skipped** — this is a personal project with a single operator. Adding DynamoDB locking adds cost and setup complexity for no practical benefit.

### D4: GitHub Actions secrets for AWS credentials

The deploy workflow uses `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` stored as GitHub repository secrets. For a personal project this is standard. For a team project, OIDC federation (no long-lived keys) would be preferred — noted as a future improvement.

### D5: Lambda Function URL (not API Gateway)

API Gateway HTTP API adds ~$1/million requests and significant Terraform complexity (stages, integrations, routes). Lambda Function URL is free, supports the same CORS and auth models, and Mangum handles it identically to API Gateway. No reason to add API Gateway for this project.

### D6: SQS event source mapping batch size 1

Both worker handlers process one message at a time (one article, one topic). Batch size 1 is correct. Increasing batch size would require the processing pipeline to handle parallelism it was not designed for.

### D7: SSM parameters as placeholders — values set manually post-provision

Terraform creates the SSM SecureString parameters with a placeholder value (`"REPLACE_ME"`). The actual secrets (Supabase URL, OpenAI key, Qdrant creds) are entered manually via the AWS console or CLI after `terraform apply`. This avoids storing secrets in Terraform state or code. The deploy workflow reads SSM values at deploy time and injects them as Lambda environment variables.

## Risks / Trade-offs

**[Risk] Terraform state in S3 is not locked** → For a solo project this is fine. If two people run `terraform apply` simultaneously, state corruption is possible. Mitigation: add DynamoDB locking table if the project gains contributors.

**[Risk] Migration Lambda invocation uses the *old* image to run migrations** → The `aws lambda invoke --payload '{"action":"migrate"}'` call happens before `update-function-code`, so it runs the currently-deployed image. If the new migration requires code that only exists in the new image, this will fail. Mitigation: only add backwards-compatible migrations (standard practice).

**[Risk] Lambda cold start on first deploy** → After `update-function-code`, the next invocation will cold-start. For the API Lambda this means ~5-10s first response. Mitigation: acceptable for a personal project; provisioned concurrency can be added later.

**[Risk] ECR image tag is commit SHA** → If a deploy fails mid-way (e.g., migration passes but Lambda update fails), the ECR image exists but Lambda still points to the previous tag. Re-running the workflow will re-push the same SHA tag (idempotent) and retry the Lambda update. No data loss risk.

**[Risk] API Lambda timeout (30s) may be too short for cold-start + slow queries** → The current read APIs are fast (Postgres queries). If a slow endpoint is added later, 30s may not be enough. Mitigation: increase timeout in Terraform if needed.

## Migration Plan

**One-time bootstrap (run once by the developer):**
1. Create S3 bucket for Terraform state: `aws s3 mb s3://storydiff-tf-state --region <region>`
2. `cd infra && terraform init`
3. `terraform apply` — provisions ECR repos, Lambda functions (with placeholder images), SQS, IAM, SSM
4. Populate SSM parameters: database URL, OpenAI key, Qdrant URL+key
5. Push a commit to `main` — the deploy workflow builds images and deploys them for the first time
6. Connect Vercel to the GitHub repo (manual, one-time)

**Rollback:**
- Lambda: `aws lambda update-function-code --function-name storydiff-api --image-uri <previous-ecr-uri>` per function
- Migrations: manual SQL or `alembic downgrade` invoked via Lambda invoke

## Open Questions

*(none — all decisions resolved above)*

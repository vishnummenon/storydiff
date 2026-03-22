## 1. Dockerfiles

- [x] 1.1 Create `backend/Dockerfile.api` — base `public.ecr.aws/lambda/python:3.11`, install uv, run `uv sync --no-dev` copying packages into `${LAMBDA_TASK_ROOT}`, copy `src/storydiff` into `${LAMBDA_TASK_ROOT}`, CMD `storydiff.lambda_api.handler`
- [x] 1.2 Create `backend/Dockerfile.analysis` — identical dependency install steps as Dockerfile.api, CMD `storydiff.analysis.lambda_handler.lambda_handler`
- [x] 1.3 Create `backend/Dockerfile.topic_refresh` — identical dependency install steps, CMD `storydiff.topic_refresh.lambda_handler.lambda_handler`
- [ ] 1.4 Verify all three images build locally with `docker build -f backend/Dockerfile.api backend/` (and the other two)

## 2. Migration handler in lambda_api.py

- [x] 2.1 Extend `backend/src/storydiff/lambda_api.py` to detect `{"action": "migrate"}` events — if detected, run `alembic upgrade head` via subprocess and return `{"migrated": true}` without invoking Mangum
- [x] 2.2 Ensure standard HTTP events (containing `requestContext` key) are still passed to the Mangum handler unchanged

## 3. GitHub Actions — Backend CI

- [x] 3.1 Create `.github/workflows/backend-ci.yml` with trigger on push/PR to `main` or `dev`, path filter `backend/**`
- [x] 3.2 Add job steps: checkout, install uv, `uv sync --group dev`, `uv run ruff check src/`
- [x] 3.3 Add `postgres:16` service container to the job with health check; set `TEST_DATABASE_URL` env var pointing to it
- [x] 3.4 Add step: `uv run pytest` — runs all tests using the Postgres service

## 4. GitHub Actions — Frontend CI

- [x] 4.1 Create `.github/workflows/frontend-ci.yml` with trigger on push/PR to `main` or `dev`, path filter `web/**`
- [x] 4.2 Add job steps: checkout, setup Node 20, `npm ci`, `npm run lint`, `npm run build`

## 5. GitHub Actions — Deploy

- [x] 5.1 Create `.github/workflows/deploy.yml` with trigger on push to `main` only
- [x] 5.2 Add step: configure AWS credentials from secrets (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`)
- [x] 5.3 Add step: ECR login via `aws ecr get-login-password | docker login`
- [x] 5.4 Add steps: build and push all three images tagged with `${{ github.sha }}` to their ECR repos
- [x] 5.5 Add step: invoke API Lambda with `{"action": "migrate"}` using `aws lambda invoke`, check response for errors, fail workflow if migration fails
- [x] 5.6 Add steps: `aws lambda update-function-code` for each of the three functions using the new image digest, followed by `aws lambda wait function-updated` before proceeding to the next

## 6. Terraform — ECR

- [x] 6.1 Create `infra/` directory at repo root
- [x] 6.2 Create `infra/main.tf` — AWS provider config, S3 backend (bucket name `storydiff-tf-state`, key `terraform.tfstate`)
- [x] 6.3 Create `infra/variables.tf` — `aws_region` variable (default `us-east-1`)
- [x] 6.4 Create `infra/ecr.tf` — three `aws_ecr_repository` resources (`storydiff-api`, `storydiff-analysis-worker`, `storydiff-topic-refresh-worker`) with MUTABLE tags and lifecycle policy keeping last 5 images

## 7. Terraform — Lambda

- [x] 7.1 Create `infra/lambda.tf` — three `aws_lambda_function` resources with `package_type = "Image"`, placeholder `image_uri` (ECR repo URL with `:latest` tag), correct memory and timeout per function
- [x] 7.2 Add `aws_lambda_function_url` for the API Lambda with `authorization_type = "NONE"`

## 8. Terraform — SQS

- [x] 8.1 Create `infra/sqs.tf` — two main queues (`storydiff-article-analyze`, `storydiff-topic-refresh`) with correct visibility timeouts and redrive policies (max_receive_count = 3)
- [x] 8.2 Add two DLQ queues with `message_retention_seconds = 604800` (7 days)
- [x] 8.3 Add two `aws_lambda_event_source_mapping` resources (article-analyze → analysis Lambda, topic-refresh → topic-refresh Lambda) with `batch_size = 1` and `function_response_types = ["ReportBatchItemFailures"]`

## 9. Terraform — IAM

- [x] 9.1 Create `infra/iam.tf` — shared Lambda execution role with `AWSLambdaBasicExecutionRole` managed policy
- [x] 9.2 Add API Lambda inline policy: SQS SendMessage on both worker queues, SSM GetParameter on `/storydiff/*`
- [x] 9.3 Add analysis worker inline policy: SQS ReceiveMessage/DeleteMessage/GetQueueAttributes on article-analyze queue + its DLQ, SSM GetParameter on `/storydiff/*`
- [x] 9.4 Add topic refresh worker inline policy: same as analysis worker but for topic-refresh queue + DLQ

## 10. Terraform — SSM and Outputs

- [x] 10.1 Create `infra/ssm.tf` — six `aws_ssm_parameter` resources as `SecureString` with value `"REPLACE_ME"`: `database-url`, `openai-api-key`, `qdrant-url`, `qdrant-api-key`, `sqs-article-analyze-queue-url`, `sqs-topic-refresh-queue-url` under `/storydiff/` prefix
- [x] 10.2 Create `infra/outputs.tf` — output API Lambda Function URL, article-analyze queue URL, topic-refresh queue URL, all three ECR repo URLs

## 11. README — Deployment Section

- [x] 11.1 Add `## Deployment` section to root `README.md` covering: prerequisites (AWS CLI, Terraform, uv), one-time bootstrap steps (create S3 state bucket → terraform init → terraform apply → populate SSM parameters → connect Vercel), ongoing workflow (GitHub Actions auto-deploys on push to main), required GitHub secrets (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, ECR_REGISTRY), how to run migrations manually

## 12. Verification

- [x] 12.1 Run `terraform validate` in `infra/` — no errors
- [x] 12.2 Run `terraform fmt -check` in `infra/` — no formatting issues
- [ ] 12.3 Confirm all three Docker images build successfully locally
- [x] 12.4 Validate GitHub Actions YAML syntax (e.g. `yamllint .github/workflows/`) — no errors

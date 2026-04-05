## ADDED Requirements

### Requirement: Three ECR repositories exist for the backend images
The system SHALL provision three ECR repositories via Terraform: `storydiff-api`, `storydiff-analysis-worker`, `storydiff-topic-refresh-worker`. Each MUST have MUTABLE image tags and a lifecycle policy retaining the last 5 images.

#### Scenario: ECR repos created by terraform apply
- **WHEN** `terraform apply` completes
- **THEN** three ECR repositories exist in the AWS account with the correct names

#### Scenario: Old images cleaned up automatically
- **WHEN** more than 5 images exist in a repository
- **THEN** the oldest images beyond the 5-image limit are automatically deleted by the lifecycle policy

### Requirement: Three Lambda functions provisioned with correct configuration
The system SHALL provision three Lambda functions via Terraform with container image package type and the following configuration:
- `storydiff-api`: 512MB memory, 30s timeout, Lambda Function URL enabled (auth NONE)
- `storydiff-analysis-worker`: 1024MB memory, 300s timeout
- `storydiff-topic-refresh-worker`: 1024MB memory, 600s timeout

#### Scenario: API Lambda Function URL is accessible
- **WHEN** Terraform provisions the API Lambda
- **THEN** a Function URL is created and output by `terraform output`

#### Scenario: Worker timeouts match SQS visibility timeouts
- **WHEN** Terraform provisions the worker Lambdas
- **THEN** the analysis Lambda timeout equals 300s and the topic refresh Lambda timeout equals 600s

### Requirement: SQS queues and DLQs provisioned with correct configuration
The system SHALL provision via Terraform:
- `storydiff-article-analyze` queue: visibility timeout 300s, DLQ after 3 receives
- `storydiff-topic-refresh` queue: visibility timeout 600s, DLQ after 3 receives
- Two DLQ queues retaining messages for 7 days
- SQS event source mappings: article-analyze → analysis Lambda, topic-refresh → topic-refresh Lambda, both with batch size 1 and `ReportBatchItemFailures` enabled

#### Scenario: Event source mappings enable partial batch failure
- **WHEN** Terraform provisions the event source mappings
- **THEN** both mappings have `function_response_types = ["ReportBatchItemFailures"]`

#### Scenario: Failed messages route to DLQ after 3 attempts
- **WHEN** a message fails processing 3 times
- **THEN** it is moved to the corresponding DLQ

### Requirement: IAM roles grant least-privilege access
The system SHALL provision via Terraform separate IAM policies per Lambda with the minimum required permissions:
- API Lambda: SQS SendMessage on both worker queues, SSM GetParameter on `/storydiff/*`
- Analysis worker Lambda: SQS ReceiveMessage/DeleteMessage/GetQueueAttributes on article-analyze queue and its DLQ, SSM GetParameter on `/storydiff/*`
- Topic refresh worker Lambda: SQS ReceiveMessage/DeleteMessage/GetQueueAttributes on topic-refresh queue and its DLQ, SSM GetParameter on `/storydiff/*`
- All Lambdas: basic execution role (CloudWatch Logs)

#### Scenario: Worker Lambdas cannot send to queues
- **WHEN** the analysis worker IAM policy is evaluated
- **THEN** SQS SendMessage is not permitted

#### Scenario: API Lambda cannot receive from queues
- **WHEN** the API Lambda IAM policy is evaluated
- **THEN** SQS ReceiveMessage is not permitted

### Requirement: SSM Parameter Store holds all runtime secrets as placeholders
The system SHALL provision via Terraform six SecureString parameters under `/storydiff/` with placeholder value `"REPLACE_ME"`. Values MUST be set manually after provisioning.

Parameters: `/storydiff/database-url`, `/storydiff/openai-api-key`, `/storydiff/qdrant-url`, `/storydiff/qdrant-api-key`, `/storydiff/sqs-article-analyze-queue-url`, `/storydiff/sqs-topic-refresh-queue-url`

#### Scenario: Parameters exist after terraform apply
- **WHEN** `terraform apply` completes
- **THEN** all six SSM parameters exist with placeholder values

#### Scenario: Secrets not stored in Terraform state in plaintext
- **WHEN** Terraform state is inspected
- **THEN** the parameter values show as `"REPLACE_ME"` (placeholders only, never real secrets)

### Requirement: Terraform state stored in S3
The system SHALL configure a Terraform S3 backend. The S3 bucket MUST be created manually before `terraform init` and its name documented in `infra/main.tf` and `README.md`.

#### Scenario: terraform init succeeds with S3 backend
- **WHEN** the S3 state bucket exists and `terraform init` is run
- **THEN** Terraform initialises successfully and stores state in S3

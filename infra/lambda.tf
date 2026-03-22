# Lambda functions use container images from ECR.
#
# image_uri is managed by the CI/CD pipeline (deploy.yml) via
# `aws lambda update-function-code`. Terraform creates the function with a
# placeholder URI pointing to :latest; after the first deploy workflow run the
# live image takes over.  `ignore_changes` prevents Terraform from reverting
# the image on subsequent `terraform apply` runs.
#
# Bootstrap order:
#   1. terraform apply -target=aws_ecr_repository.repos
#   2. Push initial images (trigger deploy workflow or push manually)
#   3. terraform apply  (creates remaining resources)

resource "aws_lambda_function" "api" {
  function_name = "storydiff-api"
  role          = aws_iam_role.lambda_api.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.repos["storydiff-api"].repository_url}:latest"

  memory_size = 512
  timeout     = 30

  environment {
    variables = {
      # SSM parameter names — the function reads these at runtime via boto3.
      # Actual values are stored in SSM, not here.
      SSM_DATABASE_URL                  = "/storydiff/database-url"
      SSM_OPENAI_API_KEY                = "/storydiff/openai-api-key"
      SSM_QDRANT_URL                    = "/storydiff/qdrant-url"
      SSM_QDRANT_API_KEY                = "/storydiff/qdrant-api-key"
      SSM_SQS_ARTICLE_ANALYZE_QUEUE_URL = "/storydiff/sqs-article-analyze-queue-url"
      SSM_SQS_TOPIC_REFRESH_QUEUE_URL   = "/storydiff/sqs-topic-refresh-queue-url"
    }
  }

  lifecycle {
    ignore_changes = [image_uri]
  }
}

resource "aws_lambda_function_url" "api" {
  function_name      = aws_lambda_function.api.function_name
  authorization_type = "NONE"
}

resource "aws_lambda_function" "analysis_worker" {
  function_name = "storydiff-analysis-worker"
  role          = aws_iam_role.lambda_analysis_worker.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.repos["storydiff-analysis-worker"].repository_url}:latest"

  memory_size = 1024
  timeout     = 300

  environment {
    variables = {
      SSM_DATABASE_URL                  = "/storydiff/database-url"
      SSM_OPENAI_API_KEY                = "/storydiff/openai-api-key"
      SSM_QDRANT_URL                    = "/storydiff/qdrant-url"
      SSM_QDRANT_API_KEY                = "/storydiff/qdrant-api-key"
      SSM_SQS_ARTICLE_ANALYZE_QUEUE_URL = "/storydiff/sqs-article-analyze-queue-url"
      SSM_SQS_TOPIC_REFRESH_QUEUE_URL   = "/storydiff/sqs-topic-refresh-queue-url"
    }
  }

  lifecycle {
    ignore_changes = [image_uri]
  }
}

resource "aws_lambda_function" "topic_refresh_worker" {
  function_name = "storydiff-topic-refresh-worker"
  role          = aws_iam_role.lambda_topic_refresh_worker.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.repos["storydiff-topic-refresh-worker"].repository_url}:latest"

  memory_size = 1024
  timeout     = 600

  environment {
    variables = {
      SSM_DATABASE_URL                  = "/storydiff/database-url"
      SSM_OPENAI_API_KEY                = "/storydiff/openai-api-key"
      SSM_QDRANT_URL                    = "/storydiff/qdrant-url"
      SSM_QDRANT_API_KEY                = "/storydiff/qdrant-api-key"
      SSM_SQS_ARTICLE_ANALYZE_QUEUE_URL = "/storydiff/sqs-article-analyze-queue-url"
      SSM_SQS_TOPIC_REFRESH_QUEUE_URL   = "/storydiff/sqs-topic-refresh-queue-url"
    }
  }

  lifecycle {
    ignore_changes = [image_uri]
  }
}

data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

# ── API Lambda ───────────────────────────────────────────────────────────────

resource "aws_iam_role" "lambda_api" {
  name               = "storydiff-lambda-api"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

resource "aws_iam_role_policy_attachment" "lambda_api_basic" {
  role       = aws_iam_role.lambda_api.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_api" {
  name = "storydiff-api-policy"
  role = aws_iam_role.lambda_api.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "SQSSend"
        Effect = "Allow"
        Action = ["sqs:SendMessage"]
        Resource = [
          aws_sqs_queue.article_analyze.arn,
          aws_sqs_queue.topic_refresh.arn,
        ]
      },
      {
        Sid      = "SSMRead"
        Effect   = "Allow"
        Action   = ["ssm:GetParameter"]
        Resource = "arn:aws:ssm:${var.aws_region}:*:parameter/storydiff/*"
      },
    ]
  })
}

# ── Analysis worker Lambda ───────────────────────────────────────────────────

resource "aws_iam_role" "lambda_analysis_worker" {
  name               = "storydiff-lambda-analysis-worker"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

resource "aws_iam_role_policy_attachment" "lambda_analysis_basic" {
  role       = aws_iam_role.lambda_analysis_worker.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_analysis_worker" {
  name = "storydiff-analysis-worker-policy"
  role = aws_iam_role.lambda_analysis_worker.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "SQSConsume"
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
        ]
        Resource = [
          aws_sqs_queue.article_analyze.arn,
          aws_sqs_queue.article_analyze_dlq.arn,
        ]
      },
      {
        Sid      = "SSMRead"
        Effect   = "Allow"
        Action   = ["ssm:GetParameter"]
        Resource = "arn:aws:ssm:${var.aws_region}:*:parameter/storydiff/*"
      },
    ]
  })
}

# ── Topic refresh worker Lambda ──────────────────────────────────────────────

resource "aws_iam_role" "lambda_topic_refresh_worker" {
  name               = "storydiff-lambda-topic-refresh-worker"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

resource "aws_iam_role_policy_attachment" "lambda_topic_refresh_basic" {
  role       = aws_iam_role.lambda_topic_refresh_worker.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_topic_refresh_worker" {
  name = "storydiff-topic-refresh-worker-policy"
  role = aws_iam_role.lambda_topic_refresh_worker.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "SQSConsume"
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
        ]
        Resource = [
          aws_sqs_queue.topic_refresh.arn,
          aws_sqs_queue.topic_refresh_dlq.arn,
        ]
      },
      {
        Sid      = "SSMRead"
        Effect   = "Allow"
        Action   = ["ssm:GetParameter"]
        Resource = "arn:aws:ssm:${var.aws_region}:*:parameter/storydiff/*"
      },
    ]
  })
}

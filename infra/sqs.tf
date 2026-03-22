# Dead-letter queues
resource "aws_sqs_queue" "article_analyze_dlq" {
  name                      = "storydiff-article-analyze-dlq"
  message_retention_seconds = 604800 # 7 days
}

resource "aws_sqs_queue" "topic_refresh_dlq" {
  name                      = "storydiff-topic-refresh-dlq"
  message_retention_seconds = 604800 # 7 days
}

# Main queues
resource "aws_sqs_queue" "article_analyze" {
  name                       = "storydiff-article-analyze"
  visibility_timeout_seconds = 300

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.article_analyze_dlq.arn
    maxReceiveCount     = 3
  })
}

resource "aws_sqs_queue" "topic_refresh" {
  name                       = "storydiff-topic-refresh"
  visibility_timeout_seconds = 600

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.topic_refresh_dlq.arn
    maxReceiveCount     = 3
  })
}

# Event source mappings — Lambda polls SQS automatically
resource "aws_lambda_event_source_mapping" "article_analyze" {
  event_source_arn        = aws_sqs_queue.article_analyze.arn
  function_name           = aws_lambda_function.analysis_worker.arn
  batch_size              = 1
  function_response_types = ["ReportBatchItemFailures"]
}

resource "aws_lambda_event_source_mapping" "topic_refresh" {
  event_source_arn        = aws_sqs_queue.topic_refresh.arn
  function_name           = aws_lambda_function.topic_refresh_worker.arn
  batch_size              = 1
  function_response_types = ["ReportBatchItemFailures"]
}

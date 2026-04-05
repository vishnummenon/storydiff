output "api_function_url" {
  description = "Lambda Function URL for the API (use as BACKEND_URL in Vercel)"
  value       = aws_lambda_function_url.api.function_url
}

output "article_analyze_queue_url" {
  description = "SQS URL for the article-analyze queue"
  value       = aws_sqs_queue.article_analyze.url
}

output "topic_refresh_queue_url" {
  description = "SQS URL for the topic-refresh queue"
  value       = aws_sqs_queue.topic_refresh.url
}

output "ecr_api_repository_url" {
  description = "ECR repository URL for the API image"
  value       = aws_ecr_repository.repos["storydiff-api"].repository_url
}

output "ecr_analysis_worker_repository_url" {
  description = "ECR repository URL for the analysis worker image"
  value       = aws_ecr_repository.repos["storydiff-analysis-worker"].repository_url
}

output "ecr_topic_refresh_worker_repository_url" {
  description = "ECR repository URL for the topic refresh worker image"
  value       = aws_ecr_repository.repos["storydiff-topic-refresh-worker"].repository_url
}

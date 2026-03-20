#!/usr/bin/env bash
# Create SQS queues in LocalStack (run after: docker compose up -d localstack).
# Safe to re-run: skips queues that already exist (does not recreate them).
set -euo pipefail

ENDPOINT="${AWS_ENDPOINT_URL:-http://localhost:4566}"
export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-test}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-test}"
export AWS_DEFAULT_REGION="${AWS_REGION:-us-east-1}"

ensure_queue() {
  local name=$1
  if aws sqs get-queue-url --endpoint-url="$ENDPOINT" --queue-name "$name" --query QueueUrl --output text >/dev/null 2>&1; then
    echo "Queue already exists (skipped): $name"
  else
    aws sqs create-queue --endpoint-url="$ENDPOINT" --queue-name "$name" >/dev/null
    echo "Created queue: $name"
  fi
}

for name in storydiff-article-ingested storydiff-article-analyze storydiff-topic-refresh; do
  ensure_queue "$name"
done

echo ""
echo "Queue URLs (set in backend/.env):"
echo "  SQS_ARTICLE_INGESTED_QUEUE_URL / SQS_ARTICLE_ANALYZE_QUEUE_URL / SQS_TOPIC_REFRESH_QUEUE_URL"
for name in storydiff-article-ingested storydiff-article-analyze storydiff-topic-refresh; do
  url=$(aws sqs get-queue-url --endpoint-url="$ENDPOINT" --queue-name "$name" --query QueueUrl --output text)
  echo "  $name -> $url"
done
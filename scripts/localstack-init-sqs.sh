#!/usr/bin/env bash
# Create SQS queues in LocalStack (run after: docker compose up -d localstack).
set -euo pipefail

ENDPOINT="${AWS_ENDPOINT_URL:-http://localhost:4566}"
export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-test}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-test}"
export AWS_DEFAULT_REGION="${AWS_REGION:-us-east-1}"

for name in storydiff-article-ingested storydiff-article-analyze; do
  aws sqs create-queue --endpoint-url="$ENDPOINT" --queue-name "$name" >/dev/null
  echo "Created queue: $name"
done

echo ""
echo "Queue URLs (set in backend/.env):"
for name in storydiff-article-ingested storydiff-article-analyze; do
  url=$(aws sqs get-queue-url --endpoint-url="$ENDPOINT" --queue-name "$name" --query QueueUrl --output text)
  echo "  $name -> $url"
done

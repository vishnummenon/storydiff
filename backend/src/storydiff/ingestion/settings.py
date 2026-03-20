"""Ingestion / AWS settings from environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_BACKEND_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class IngestionSettings:
    aws_region: str
    aws_endpoint_url: str | None
    sqs_article_ingested_queue_url: str | None
    sqs_article_analyze_queue_url: str | None
    sqs_topic_refresh_queue_url: str | None


def load_ingestion_settings() -> IngestionSettings:
    load_dotenv(_BACKEND_ROOT / ".env")
    region = os.environ.get("AWS_REGION", "us-east-1").strip()
    endpoint = os.environ.get("AWS_ENDPOINT_URL", "").strip() or None
    ingested = os.environ.get("SQS_ARTICLE_INGESTED_QUEUE_URL", "").strip() or None
    analyze = os.environ.get("SQS_ARTICLE_ANALYZE_QUEUE_URL", "").strip() or None
    topic_refresh = os.environ.get("SQS_TOPIC_REFRESH_QUEUE_URL", "").strip() or None
    return IngestionSettings(
        aws_region=region,
        aws_endpoint_url=endpoint,
        sqs_article_ingested_queue_url=ingested,
        sqs_article_analyze_queue_url=analyze,
        sqs_topic_refresh_queue_url=topic_refresh,
    )

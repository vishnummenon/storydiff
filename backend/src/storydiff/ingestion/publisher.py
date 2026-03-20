"""SQS publisher for article.ingested and article.analyze (architecture/events.md §7)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Protocol

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from storydiff.ingestion.settings import IngestionSettings, load_ingestion_settings

logger = logging.getLogger(__name__)


def utc_iso_z(dt: datetime | None = None) -> str:
    if dt is None:
        dt = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class EventPublisher(Protocol):
    def publish_article_ingested(self, payload: dict[str, Any]) -> None: ...

    def publish_article_analyze(self, payload: dict[str, Any]) -> None: ...

    def publish_topic_refresh(self, payload: dict[str, Any]) -> None: ...


class SqsPublisher:
    """Send JSON messages to configured SQS queue URLs."""

    def __init__(self, settings: IngestionSettings | None = None) -> None:
        self._settings = settings or load_ingestion_settings()
        self._client = boto3.client(
            "sqs",
            region_name=self._settings.aws_region,
            endpoint_url=self._settings.aws_endpoint_url,
        )

    def publish_article_ingested(self, payload: dict[str, Any]) -> None:
        self._send(self._settings.sqs_article_ingested_queue_url, payload, "article.ingested")

    def publish_article_analyze(self, payload: dict[str, Any]) -> None:
        self._send(self._settings.sqs_article_analyze_queue_url, payload, "article.analyze")

    def publish_topic_refresh(self, payload: dict[str, Any]) -> None:
        self._send(self._settings.sqs_topic_refresh_queue_url, payload, "topic.refresh")

    def _send(self, queue_url: str | None, payload: dict[str, Any], label: str) -> None:
        if not queue_url:
            logger.debug("Skipping SQS publish for %s: queue URL not configured", label)
            return
        body = json.dumps(payload, separators=(",", ":"))
        try:
            self._client.send_message(QueueUrl=queue_url, MessageBody=body)
        except (ClientError, BotoCoreError) as e:
            logger.exception("SQS publish failed for %s: %s", label, e)
            raise


class NoopPublisher:
    """Drop events (e.g. tests)."""

    def publish_article_ingested(self, payload: dict[str, Any]) -> None:
        return

    def publish_article_analyze(self, payload: dict[str, Any]) -> None:
        return

    def publish_topic_refresh(self, payload: dict[str, Any]) -> None:
        return

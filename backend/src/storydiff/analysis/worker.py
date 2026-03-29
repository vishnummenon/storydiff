"""SQS long-poll worker for ``article.analyze`` messages."""

from __future__ import annotations

import atexit
import json
import logging
import signal
import sys
from typing import Any

import boto3

from storydiff.analysis.checkpointing import close_checkpoint_resources
from storydiff.analysis.pipeline import process_article_analysis_swallow
from storydiff.ingestion.settings import load_ingestion_settings
from storydiff.observability import init_netra

logger = logging.getLogger(__name__)

_stop = False


def _handle_sigint(_sig: int, _frame: Any) -> None:
    global _stop
    _stop = True
    logger.info("Shutdown requested, finishing current batch…")


def run_worker(*, wait_seconds: int = 20, max_messages: int = 1) -> None:
    init_netra("storydiff-analysis-worker")
    atexit.register(close_checkpoint_resources)
    settings = load_ingestion_settings()
    queue_url = settings.sqs_article_analyze_queue_url
    if not queue_url:
        raise RuntimeError("SQS_ARTICLE_ANALYZE_QUEUE_URL must be set for the analysis worker")

    client = boto3.client(
        "sqs",
        region_name=settings.aws_region,
        endpoint_url=settings.aws_endpoint_url,
    )
    signal.signal(signal.SIGINT, _handle_sigint)
    signal.signal(signal.SIGTERM, _handle_sigint)

    logger.info("Analysis worker polling %s", queue_url)
    while not _stop:
        try:
            resp = client.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=max_messages,
                WaitTimeSeconds=wait_seconds,
                VisibilityTimeout=300,
            )
        except Exception:
            if _stop:
                break
            raise
        messages = resp.get("Messages") or []
        if not messages:
            continue
        for msg in messages:
            receipt = msg["ReceiptHandle"]
            body = msg.get("Body", "")
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                logger.error("Invalid JSON, deleting poison message: %s", body[:200])
                client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt)
                continue
            if payload.get("event_type") != "article.analyze":
                logger.warning("Unknown event_type %r, deleting", payload.get("event_type"))
                client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt)
                continue
            article_id = payload.get("article_id")
            if article_id is None:
                logger.error("Missing article_id, deleting message")
                client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt)
                continue
            try:
                aid = int(article_id)
            except (TypeError, ValueError):
                logger.error("Invalid article_id %r", article_id)
                client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt)
                continue

            logger.info("Processing article_id=%s", aid)
            out = process_article_analysis_swallow(aid)
            if out.get("ok"):
                client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt)
                logger.info("Done article_id=%s", aid)
            else:
                # Leave message for retry; visibility timeout will expire
                logger.error("Failed article_id=%s: %s", aid, out.get("error"))


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    try:
        run_worker()
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()

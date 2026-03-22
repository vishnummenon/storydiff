"""AWS Lambda entry point for the article analysis worker.

AWS Lambda with an SQS event source mapping invokes this handler with a batch
of pre-fetched SQS records.  Each record carries one ``article.analyze`` event.

Partial batch failure reporting is enabled: if one record fails, only that
record's ``messageId`` is returned in ``batchItemFailures`` so it is retried
independently.  The SQS event source mapping must have
``FunctionResponseTypes: ["ReportBatchItemFailures"]`` configured (done in
the infra change).

Local dev is unaffected — use ``python -m storydiff.analysis`` as before.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from storydiff.analysis.pipeline import process_article_analysis_swallow

logger = logging.getLogger(__name__)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:  # noqa: ARG001
    batch_item_failures: list[dict[str, str]] = []

    for record in event.get("Records", []):
        message_id = record.get("messageId", "<unknown>")
        body = record.get("body", "")

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            logger.error("Invalid JSON in message %s: %s", message_id, body[:200])
            batch_item_failures.append({"itemIdentifier": message_id})
            continue

        if payload.get("event_type") != "article.analyze":
            logger.error(
                "Unexpected event_type %r in message %s — routing to DLQ",
                payload.get("event_type"),
                message_id,
            )
            batch_item_failures.append({"itemIdentifier": message_id})
            continue

        article_id = payload.get("article_id")
        if article_id is None:
            logger.error("Missing article_id in message %s", message_id)
            batch_item_failures.append({"itemIdentifier": message_id})
            continue

        try:
            aid = int(article_id)
        except (TypeError, ValueError):
            logger.error("Invalid article_id %r in message %s", article_id, message_id)
            batch_item_failures.append({"itemIdentifier": message_id})
            continue

        try:
            result = process_article_analysis_swallow(aid)
        except Exception:
            logger.exception("Unhandled exception processing article_id=%s (message %s)", aid, message_id)
            batch_item_failures.append({"itemIdentifier": message_id})
            continue

        if not result.get("ok"):
            logger.error(
                "Processing failed for article_id=%s (message %s): %s",
                aid,
                message_id,
                result.get("error"),
            )
            batch_item_failures.append({"itemIdentifier": message_id})
        else:
            logger.info("Processed article_id=%s (message %s)", aid, message_id)

    return {"batchItemFailures": batch_item_failures}

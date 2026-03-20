"""Integration-style test: SQS publish via moto."""

from __future__ import annotations

import json

import boto3
from moto import mock_aws

from storydiff.ingestion.publisher import SqsPublisher
from storydiff.ingestion.settings import IngestionSettings


@mock_aws
def test_sqs_publisher_sends_json_message():
    sqs = boto3.client("sqs", region_name="us-east-1")
    ingested_url = sqs.create_queue(QueueName="article-ingested")["QueueUrl"]
    analyze_url = sqs.create_queue(QueueName="article-analyze")["QueueUrl"]

    settings = IngestionSettings(
        aws_region="us-east-1",
        aws_endpoint_url=None,
        sqs_article_ingested_queue_url=ingested_url,
        sqs_article_analyze_queue_url=analyze_url,
        sqs_topic_refresh_queue_url=None,
    )

    pub = SqsPublisher(settings=settings)
    pub.publish_article_ingested(
        {
            "event_type": "article.ingested",
            "article_id": 1,
            "media_outlet_id": 2,
            "published_at": "2026-03-20T08:00:00Z",
            "dedupe_status": "inserted",
            "occurred_at": "2026-03-20T08:01:00Z",
        }
    )

    msgs = sqs.receive_message(QueueUrl=ingested_url, MessageAttributeNames=["All"]).get(
        "Messages", []
    )
    assert len(msgs) == 1
    data = json.loads(msgs[0]["Body"])
    assert data["event_type"] == "article.ingested"
    assert data["article_id"] == 1

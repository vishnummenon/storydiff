"""FastAPI dependencies for ingestion."""

from __future__ import annotations

from storydiff.ingestion.publisher import EventPublisher, SqsPublisher
from storydiff.ingestion.service import IngestionService


def get_publisher() -> EventPublisher:
    return SqsPublisher()


def get_ingestion_service() -> IngestionService:
    return IngestionService()

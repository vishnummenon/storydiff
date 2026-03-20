"""HTTP routes for ingestion (thin handlers)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from storydiff.db.session import get_db
from storydiff.ingestion.deps import get_ingestion_service, get_publisher
from storydiff.ingestion.publisher import EventPublisher
from storydiff.ingestion.schemas import IngestRequest, IngestSuccessData
from storydiff.ingestion.service import IngestionService
from storydiff.ingestion.envelope import success_response

router = APIRouter(tags=["ingestion"])


@router.post("/ingest")
def post_ingest(
    body: IngestRequest,
    session: Session = Depends(get_db),
    service: IngestionService = Depends(get_ingestion_service),
    publisher: EventPublisher = Depends(get_publisher),
):
    result = service.ingest(session, body, publisher)
    data = IngestSuccessData.model_validate(
        {
            "article_id": result.article_id,
            "dedupe_status": result.dedupe_status,
            "processing_status": result.processing_status,
        }
    )
    return success_response(data)

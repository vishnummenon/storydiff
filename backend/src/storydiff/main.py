"""FastAPI application entry."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from storydiff.ingestion.exceptions import IngestionClientError
from storydiff.ingestion.envelope import error_response
from storydiff.ingestion.router import router as ingest_router

app = FastAPI(title="StoryDiff API", version="0.1.0")
app.include_router(ingest_router, prefix="/api/v1")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(IngestionClientError)
async def ingestion_client_error_handler(_request, exc: IngestionClientError):
    return error_response(exc.code, exc.message, exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_request, exc: RequestValidationError):
    errors = exc.errors()
    if errors:
        first = errors[0]
        loc = ".".join(str(x) for x in first.get("loc", ()))
        msg = first.get("msg", "Validation error")
        message = f"{loc}: {msg}" if loc else msg
    else:
        message = "Validation error"
    return error_response("VALIDATION_ERROR", message, 422)

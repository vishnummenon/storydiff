"""AWS Lambda entry point for the FastAPI application.

The Mangum adapter translates Lambda HTTP events (Function URL / API Gateway
HTTP API) into ASGI calls, allowing the existing FastAPI app to run on Lambda
without any changes to routes or middleware.

This module also handles a special ``{"action": "migrate"}`` event used by the
deploy pipeline to run Alembic migrations before swapping the live function
image.  The migration event is detected before Mangum so that normal HTTP
events are unaffected.

Local dev is unaffected — use ``uvicorn storydiff.main:app`` as before.
"""

from __future__ import annotations

import logging
import subprocess
import sys
from typing import Any

from mangum import Mangum

from storydiff.main import app

logger = logging.getLogger(__name__)

_mangum_handler = Mangum(app, lifespan="off")


def handler(event: dict[str, Any], context: Any) -> Any:  # noqa: ARG001
    """Lambda entry point.

    Handles two event shapes:
    - ``{"action": "migrate"}`` — runs Alembic migrations and returns
      ``{"migrated": True}``.  Used by the deploy pipeline.
    - Any event with ``"requestContext"`` — treated as an HTTP event and
      delegated to the Mangum handler.
    """
    if event.get("action") == "migrate":
        logger.info("Running Alembic migrations")
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.error("Migration failed: %s", result.stderr)
            raise RuntimeError(f"Alembic migration failed:\n{result.stderr}")
        logger.info("Migrations complete: %s", result.stdout.strip())
        return {"migrated": True}

    return _mangum_handler(event, context)

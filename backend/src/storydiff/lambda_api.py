"""AWS Lambda entry point for the FastAPI application.

The Mangum adapter translates Lambda HTTP events (Function URL / API Gateway
HTTP API) into ASGI calls, allowing the existing FastAPI app to run on Lambda
without any changes to routes or middleware.

Local dev is unaffected — use ``uvicorn storydiff.main:app`` as before.
"""

from __future__ import annotations

from mangum import Mangum

from storydiff.main import app

handler = Mangum(app, lifespan="off")

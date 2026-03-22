"""JSON response envelope helpers (architecture/api_contract.md)."""

from __future__ import annotations

from typing import Any

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


def success_response(data: Any, meta: dict[str, Any] | None = None, status_code: int = 200) -> JSONResponse:
    body = {"data": jsonable_encoder(data), "meta": meta or {}, "error": None}
    return JSONResponse(content=body, status_code=status_code)


def error_response(code: str, message: str, status_code: int, meta: dict[str, Any] | None = None) -> JSONResponse:
    body = {"data": None, "meta": meta or {}, "error": {"code": code, "message": message}}
    return JSONResponse(content=body, status_code=status_code)

"""Week 3 API error envelope helpers (see docs/week-3-specification.md §4.4)."""

from __future__ import annotations

import uuid

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.schemas.ranking import ErrorField, ErrorResponse


def request_id_from(request: Request) -> str:
    return request.headers.get("x-request-id") or str(uuid.uuid4())


def validation_error_response(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        raise exc
    request_id = request_id_from(request)
    field_errors: list[ErrorField] = []
    for err in exc.errors():
        loc = err.get("loc") or ()
        field = ".".join(str(part) for part in loc) if loc else "body"
        reason = str(err.get("msg", "validation error"))
        field_errors.append(ErrorField(field=field, reason=reason))
    payload = ErrorResponse(
        code="validation_error",
        message="Request validation failed",
        field_errors=field_errors,
        request_id=request_id,
    )
    return JSONResponse(
        status_code=422,
        content=payload.model_dump(mode="json"),
    )


def error_json_response(
    *,
    status_code: int,
    request: Request,
    code: str,
    message: str,
    field_errors: list[ErrorField] | None = None,
) -> JSONResponse:
    payload = ErrorResponse(
        code=code,
        message=message,
        field_errors=field_errors or [],
        request_id=request_id_from(request),
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))

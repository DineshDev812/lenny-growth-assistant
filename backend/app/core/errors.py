from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import InterfaceError, OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppError, DatabaseUnavailableError

logger = logging.getLogger(__name__)


def _request_id(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    if isinstance(request_id, str) and request_id:
        return request_id
    return str(uuid4())


def error_body(code: str, message: str, request_id: str) -> dict[str, dict[str, str]]:
    return {"error": {"code": code, "message": message, "request_id": request_id}}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        request_id = _request_id(request)
        logger.warning(
            exc.message,
            extra={
                "request_id": request_id,
                "error_class": exc.code,
                "event": "app_error",
            },
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(exc.code, exc.message, request_id),
            headers={"X-Request-ID": request_id},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        request_id = _request_id(request)
        first = exc.errors()[0] if exc.errors() else None
        if first:
            location = ".".join(str(part) for part in first.get("loc", ()))
            message = f"Validation failed: {location} {first.get('msg', 'invalid')}".strip()
        else:
            message = "Request validation failed."
        return JSONResponse(
            status_code=422,
            content=error_body("validation_error", message, request_id),
            headers={"X-Request-ID": request_id},
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        request_id = _request_id(request)
        code = "http_error"
        if exc.status_code == 404:
            code = "not_found"
        elif exc.status_code == 405:
            code = "method_not_allowed"
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(code, str(exc.detail), request_id),
            headers={"X-Request-ID": request_id},
        )

    @app.exception_handler(OperationalError)
    @app.exception_handler(InterfaceError)
    async def db_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = _request_id(request)
        logger.error(
            "Database connection failed",
            extra={"request_id": request_id, "error_class": "db_down", "event": "db_error"},
            exc_info=exc,
        )
        down = DatabaseUnavailableError()
        return JSONResponse(
            status_code=down.status_code,
            content=error_body(down.code, down.message, request_id),
            headers={"X-Request-ID": request_id},
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = _request_id(request)
        logger.exception(
            "Unhandled error",
            extra={"request_id": request_id, "error_class": "internal_error", "event": "unhandled"},
        )
        return JSONResponse(
            status_code=500,
            content=error_body(
                "internal_error",
                "An unexpected error occurred.",
                request_id,
            ),
            headers={"X-Request-ID": request_id},
        )

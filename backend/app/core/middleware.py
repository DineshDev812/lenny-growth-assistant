from __future__ import annotations

import logging
import time
from uuid import uuid4

from starlette.datastructures import MutableHeaders
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import get_settings
from app.core.cookies import sign_client_id, try_unsign_client_id

logger = logging.getLogger(__name__)


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = ""
        for key, value in scope.get("headers", []):
            if key == b"x-request-id":
                request_id = value.decode("latin-1")
                break
        if not request_id:
            request_id = str(uuid4())

        state = scope.setdefault("state", {})
        state["request_id"] = request_id
        started = time.perf_counter()
        status_code = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = request_id
            await send(message)

        await self.app(scope, receive, send_wrapper)
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        session_id = state.get("session_id")
        client_id = state.get("client_id")
        path = scope.get("path", "")
        method = scope.get("method", "")
        logger.info(
            "request_completed",
            extra={
                "event": "request_completed",
                "request_id": request_id,
                "session_id": str(session_id) if session_id else None,
                "client_id": str(client_id) if client_id else None,
                "provider": get_settings().model_provider,
                "latency_ms": latency_ms,
                "path": path,
                "method": method,
                "status_code": status_code,
            },
        )


class ClientIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        settings = get_settings()
        request = Request(scope, receive)
        existing = try_unsign_client_id(request.cookies.get(settings.cookie_name))
        issued = existing is None
        client_id = existing or uuid4()
        scope.setdefault("state", {})["client_id"] = client_id

        async def send_wrapper(message: Message) -> None:
            if issued and message["type"] == "http.response.start":
                tmp = Response()
                tmp.set_cookie(
                    key=settings.cookie_name,
                    value=sign_client_id(client_id),
                    httponly=True,
                    samesite=settings.cookie_samesite,
                    secure=settings.cookie_secure,
                    max_age=60 * 60 * 24 * 365,
                    path="/",
                )
                headers = MutableHeaders(scope=message)
                headers.append("set-cookie", tmp.headers["set-cookie"])
            await send(message)

        await self.app(scope, receive, send_wrapper)


_rate_limit_records: dict[str, list[float]] = {}


def reset_rate_limits() -> None:
    """Clear in-memory rate limit records (used in tests)."""
    _rate_limit_records.clear()


class RateLimitMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "").upper()
        if method == "OPTIONS":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        # Exempt health, meta, and docs
        if path in {"/health", "/api/meta", "/docs", "/openapi.json", "/api/ingest/status"}:
            await self.app(scope, receive, send)
            return

        settings = get_settings()
        limit = settings.rate_limit_per_minute

        state = scope.setdefault("state", {})
        client_id_val = state.get("client_id")
        key = str(client_id_val) if client_id_val else "anonymous"

        now = time.monotonic()
        history = _rate_limit_records.setdefault(key, [])
        cutoff = now - 60.0
        _rate_limit_records[key] = [t for t in history if t > cutoff]
        history = _rate_limit_records[key]

        if len(history) >= limit:
            request_id = state.get("request_id")
            if not request_id:
                for h_name, h_val in scope.get("headers", []):
                    if h_name == b"x-request-id":
                        request_id = h_val.decode("latin-1")
                        break
            if not request_id:
                request_id = str(uuid4())

            logger.warning(
                "Rate limit exceeded for client %s",
                key,
                extra={
                    "event": "rate_limited",
                    "client_id": key,
                    "request_id": str(request_id),
                    "error_class": "rate_limited",
                },
            )

            import json
            payload = json.dumps({
                "error": {
                    "code": "rate_limited",
                    "message": "Too many requests. Please wait before trying again.",
                    "request_id": str(request_id),
                }
            }).encode("utf-8")

            headers = [
                (b"content-type", b"application/json"),
                (b"retry-after", b"60"),
                (b"x-request-id", str(request_id).encode("latin-1")),
            ]

            await send({
                "type": "http.response.start",
                "status": 429,
                "headers": headers,
            })
            await send({
                "type": "http.response.body",
                "body": payload,
            })
            return

        history.append(now)
        await self.app(scope, receive, send)

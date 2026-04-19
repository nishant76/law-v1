"""
Request logging middleware — logs all API calls with request_id
"""
import uuid
import time
from fastapi import Request
from starlette.types import ASGIApp, Receive, Scope, Send
from backend.core.logger import get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware:
    """Log all requests with request_id, duration, and response status.

    Implemented as a pure ASGI middleware (not BaseHTTPMiddleware) to avoid
    Starlette's known issue where BaseHTTPMiddleware breaks multipart uploads
    by consuming the request body before it reaches route handlers.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        request_id = str(uuid.uuid4())
        scope["state"] = getattr(scope, "state", {})
        request.state.request_id = request_id

        start_time = time.time()
        status_code = 500

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                message["headers"] = list(message.get("headers", [])) + [
                    (b"x-request-id", request_id.encode())
                ]
            await send(message)

        await self.app(scope, receive, send_wrapper)

        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            f"{request.method} {request.url.path} — {status_code}",
            extra={
                "request_id": request_id,
                "duration_ms": round(duration_ms, 2),
                "status_code": status_code,
            },
        )

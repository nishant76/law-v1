"""
SuperAdvocate backend — FastAPI application
Main entry point for all API routes and middleware
"""
import os
import sys
import asyncio

# On Windows, asyncio.new_event_loop() creates SelectorEventLoop by default.
# SelectorEventLoop cannot spawn subprocesses (raises NotImplementedError in
# _make_subprocess_transport). Playwright's sync_api internally creates a new
# event loop to drive its Node.js driver subprocess — so we must switch to
# ProactorEventLoop before anything starts.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware import Middleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.types import ASGIApp
from fastapi.middleware.cors import CORSMiddleware
from backend.core.config import settings
import celery_app  # noqa: F401 — ensures Celery app is initialised before any shared_task calls
from backend.middleware.logging import RequestLoggingMiddleware
from backend.api.health import router as health_router
from backend.api.documents import router as documents_router
from backend.api.search import router as search_router
from backend.api.citations import router as citations_router
from backend.api.auth import router as auth_router
from backend.api.synopsis import router as synopsis_router
from backend.api.extractor import router as extractor_router
from backend.api.deadlines import router as deadlines_router
from backend.api.reply import router as reply_router
from backend.api.filing import router as filing_router
from backend.api.legal_process import router as legal_process_router
from backend.api.ecourts import router as ecourts_router
from backend.api.matters import router as matters_router
from backend.core.logger import get_logger

logger = get_logger(__name__)

# Base allowed origins
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://localhost:4173",
    "http://localhost:8081",
    "http://localhost:8082",
]

# Add production frontend URL from environment
frontend_url = os.environ.get("FRONTEND_URL", "")
if frontend_url:
    ALLOWED_ORIGINS.append(frontend_url)
    ALLOWED_ORIGINS.append(frontend_url.rstrip("/"))


class SelectiveGZipMiddleware:
    """
    GZip compression that explicitly skips SSE (text/event-stream) endpoints.

    Implemented as a raw ASGI middleware (not BaseHTTPMiddleware) so that we
    have direct access to the ASGI `send` callable — BaseHTTPMiddleware wraps
    the request into a _CachedRequest which does NOT expose `send`, causing
    an AttributeError at runtime.

    Skips compression when:
      - The request path ends with /stream
      - The client sends Accept-Encoding: identity
    All other requests are forwarded to Starlette's GZipMiddleware.
    """

    def __init__(self, app: ASGIApp, minimum_size: int = 1000) -> None:
        self._app = app
        self._gzip_app = GZipMiddleware(app, minimum_size=minimum_size)

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        path = scope.get("path", "")
        headers = dict(scope.get("headers", []))
        accept_enc = headers.get(b"accept-encoding", b"").decode("latin-1")

        if path.endswith("/stream") or "identity" in accept_enc:
            # Bypass gzip — pass straight through to the inner app
            await self._app(scope, receive, send)
        else:
            await self._gzip_app(scope, receive, send)


# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    description="AI-powered legal workspace for solo lawyers in Punjab, Haryana, and Chandigarh",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Include routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(search_router)
app.include_router(citations_router)
app.include_router(synopsis_router)
app.include_router(extractor_router)
app.include_router(deadlines_router)
app.include_router(reply_router)
app.include_router(filing_router)
app.include_router(legal_process_router)
app.include_router(ecourts_router)
app.include_router(matters_router)


@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info(f"SuperAdvocate starting — environment={settings.ENVIRONMENT}")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    logger.info("SuperAdvocate shutting down")


# Wrap the fully-configured FastAPI app with selective gzip.
# Done last so all routers and lifecycle hooks are registered first.
# Raw ASGI middleware — avoids the _CachedRequest.send AttributeError
# that BaseHTTPMiddleware causes on newer Starlette versions.
app = SelectiveGZipMiddleware(app, minimum_size=1000)  # type: ignore[assignment]


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.DEBUG,
        log_level="info",
    )

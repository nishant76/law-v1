"""
Nikhar backend — FastAPI application
Main entry point for all API routes and middleware
"""
import os
from fastapi import FastAPI, Request
from fastapi.middleware import Middleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from fastapi.middleware.cors import CORSMiddleware
from backend.core.config import settings
import celery_app  # noqa: F401 — ensures Celery app is initialised before any shared_task calls
from backend.middleware.logging import RequestLoggingMiddleware
from backend.api.health import router as health_router
from backend.api.documents import router as documents_router
from backend.api.search import router as search_router
from backend.api.auth import router as auth_router
from backend.api.synopsis import router as synopsis_router
from backend.api.extractor import router as extractor_router
from backend.api.deadlines import router as deadlines_router
from backend.api.reply import router as reply_router
from backend.api.filing import router as filing_router
from backend.api.legal_process import router as legal_process_router
from backend.core.logger import get_logger

logger = get_logger(__name__)

# Base allowed origins
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://localhost:4173",
]

# Add production frontend URL from environment
frontend_url = os.environ.get("FRONTEND_URL", "")
if frontend_url:
    ALLOWED_ORIGINS.append(frontend_url)
    ALLOWED_ORIGINS.append(frontend_url.rstrip("/"))


class SelectiveGZipMiddleware(BaseHTTPMiddleware):
    """
    GZip compression that explicitly skips SSE (text/event-stream) endpoints.

    Starlette's built-in GZipMiddleware compresses streaming responses, which
    causes the browser to buffer the entire gzip stream before decompressing —
    destroying the real-time streaming effect on /extract/upload/stream and any
    other SSE endpoints we add in future.

    This middleware skips compression when:
      - The request path ends with /stream
      - The client sends Accept-Encoding: identity
      - The response Content-Type is text/event-stream
    """

    def __init__(self, app: ASGIApp, minimum_size: int = 1000) -> None:
        super().__init__(app)
        self._gzip_app = GZipMiddleware(app, minimum_size=minimum_size)

    async def dispatch(self, request: Request, call_next):
        # Skip gzip for streaming / SSE endpoints
        path = request.url.path
        accept_enc = request.headers.get("accept-encoding", "")
        if path.endswith("/stream") or "identity" in accept_enc:
            return await call_next(request)
        # All other responses go through normal gzip compression
        return await self._gzip_app(request.scope, request.receive, request.send)


# Middleware stack
middleware = [
    Middleware(SelectiveGZipMiddleware, minimum_size=1000),
]

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    description="AI-powered legal workspace for solo lawyers in Punjab, Haryana, and Chandigarh",
    middleware=middleware,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware after FastAPI app initialization
# (must be added after other middleware)
app.add_middleware(RequestLoggingMiddleware)

# Include routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(search_router)
app.include_router(synopsis_router)
app.include_router(extractor_router)
app.include_router(deadlines_router)
app.include_router(reply_router)
app.include_router(filing_router)
app.include_router(legal_process_router)


@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info(f"Nikhar starting — environment={settings.ENVIRONMENT}")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    logger.info("Nikhar shutting down")


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

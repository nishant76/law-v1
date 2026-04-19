"""
Nikhar backend — FastAPI application
Main entry point for all API routes and middleware
"""
from fastapi import FastAPI
from fastapi.middleware import Middleware
from starlette.middleware.gzip import GZipMiddleware
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

# Middleware stack in correct order
# 1. GZipMiddleware (compress responses)
# 2. CORSMiddleware (cross-origin requests)
# 3. RequestLoggingMiddleware (log all requests)
middleware = [
    Middleware(GZipMiddleware, minimum_size=1000),
    Middleware(
        CORSMiddleware,
        allow_origins=["https://law.nikhar.ai"] if settings.ENVIRONMENT == "production" else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    ),
]

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    description="AI-powered legal workspace for solo lawyers in Punjab, Haryana, and Chandigarh",
    middleware=middleware,
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
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info",
    )

"""
FastAPI application entry point.

Configures lifespan events (DB connect / disconnect), registers
routers, and exposes a health-check endpoint.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database.mongodb import close_mongodb_connection, connect_to_mongodb
from app.routes.metadata import router as metadata_router
from app.services.collector import close_http_client, create_http_client

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Application lifespan (startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown events."""
    # Startup
    logger.info("Starting up …")
    create_http_client()
    await connect_to_mongodb()
    logger.info("Application is ready.")

    yield

    # Shutdown
    logger.info("Shutting down …")
    await close_http_client()
    await close_mongodb_connection()
    logger.info("Shutdown complete.")


# ---------------------------------------------------------------------------
# FastAPI app instance
# ---------------------------------------------------------------------------

app = FastAPI(
    title="HTTP Metadata Inventory Service",
    description=(
        "A service that collects and retrieves HTTP metadata "
        "(headers, cookies, page source) for any given URL."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow all origins for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(metadata_router, prefix="/api/v1")


# ---------------------------------------------------------------------------
# Global exception handler
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler so unhandled errors return structured JSON."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please try again later."},
    )


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["Health"], summary="Health check")
async def health_check() -> dict:
    """Simple liveness probe."""
    return {"status": "ok"}

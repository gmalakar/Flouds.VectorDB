# =============================================================================
# File: main.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import signal
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.app_init import APP_SETTINGS
from app.config.validation import validate_config
from app.logger import get_logger
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.middleware.metrics import MetricsMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.milvus.milvus_helper import MilvusHelper
from app.routers import metrics, user, vector

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        validate_config()
        logger.info("Configuration validated successfully.")
    except Exception as e:
        logger.error(f"Configuration validation failed: {str(e)}")
        sys.exit("Configuration validation failed. Exiting application.")

    if APP_SETTINGS.vectordb:
        try:
            MilvusHelper.initialize()
            logger.info("Milvus connection initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Milvus connection: {str(e)}")
            sys.exit("Failed to initialize Milvus connection. Exiting application.")
    else:
        logger.warning(
            "VectorDB configuration is not set. Skipping Milvus initialization."
        )
        sys.exit("VectorDB configuration is not set. Exiting application.")
    yield


app = FastAPI(
    title="Flouds Vector API",
    description="Multi-tenant vector database API with Milvus backend",
    version="1.0.0",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    lifespan=lifespan,
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(RateLimitMiddleware, calls=100, period=60)
app.add_middleware(MetricsMiddleware)

app.include_router(vector.router, prefix="/api/v1/vector_store", tags=["Vector Store"])
app.include_router(
    user.router, prefix="/api/v1/vector_store_users", tags=["User Management"]
)
app.include_router(metrics.router, prefix="/api/v1", tags=["Monitoring"])


@app.get("/")
def root() -> dict:
    """Root endpoint for health check."""
    return {"message": "Flouds Vector API is running"}


@app.get("/health")
def health() -> dict:
    """Health check endpoint."""
    try:
        # Check Milvus connection
        MilvusHelper.get_connection().list_collections()
        milvus_status = "healthy"
    except:
        milvus_status = "unhealthy"

    return {
        "status": "healthy" if milvus_status == "healthy" else "degraded",
        "service": "Flouds Vector",
        "milvus": milvus_status,
    }


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    sys.exit(0)


def run_server():
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    logger.info(
        f"Starting server: uvicorn on {APP_SETTINGS.server.host}:{APP_SETTINGS.server.port}"
    )

    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=APP_SETTINGS.server.host,
        port=APP_SETTINGS.server.port,
        workers=None,
        reload=not APP_SETTINGS.app.is_production,
        log_level="info" if not APP_SETTINGS.app.debug else "debug",
        access_log=True,
    )


if __name__ == "__main__":
    try:
        run_server()
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error("Fatal error:", exc_info=e)
        sys.exit(1)

# Run Instruction
# Unit Test : python -m pytest
# Run for terminal: python -m app.main

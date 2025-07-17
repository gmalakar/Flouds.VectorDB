# =============================================================================
# File: main.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import asyncio
import signal
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header

from app.app_init import APP_SETTINGS
from app.logger import get_logger
from app.milvus.milvus_helper import MilvusHelper
from app.routers import user, vector

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
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
    description="API for Flouds Vector, a cloud-based vector database.",
    version="1.0.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.include_router(vector.router)
app.include_router(user.router)


@app.get("/")
def root() -> dict:
    """Root endpoint for health check."""
    return {"message": "Flouds Vector API is running"}


@app.get("/health")
def health() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "service": "Flouds Vector"}


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    sys.exit(0)


def run_server():
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    logger.info(
        f"Starting server: {APP_SETTINGS.server.type} on {APP_SETTINGS.server.host}:{APP_SETTINGS.server.port}"
    )
    server_type = APP_SETTINGS.server.type.lower()

    if server_type == "hypercorn":
        try:
            from hypercorn.asyncio import serve
            from hypercorn.config import Config
        except ImportError:
            logger.error("hypercorn is not installed. Falling back to uvicorn.")
            server_type = "uvicorn"

    if server_type == "hypercorn":
        config = Config()
        config.bind = [f"{APP_SETTINGS.server.host}:{APP_SETTINGS.server.port}"]
        config.reload = not APP_SETTINGS.app.is_production
        asyncio.run(serve(app, config))
    else:
        # Default to uvicorn
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

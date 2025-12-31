# =============================================================================
# File: main.py
# Description: FastAPI application entry point with middleware and lifecycle management
# Author: Goutam Malakar
# Date: 2025-01-15
# Version: 1.0.0
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import signal
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.app_init import APP_SETTINGS
from app.config.startup_validator import validate_startup_config
from app.exceptions.custom_exceptions import MilvusConnectionError
from app.logger import get_logger
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.middleware.metrics import MetricsMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_logging import RequestLoggingMiddleware
from app.middleware.validation import ValidationMiddleware
from app.milvus.milvus_helper import MilvusHelper
from app.routers import health, metrics, user, vector
from app.tasks.cleanup import cleanup_connections
from app.utils.log_sanitizer import sanitize_for_log

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown operations.

    Args:
        app (FastAPI): The FastAPI application instance

    Yields:
        None: Control back to the application during runtime
    """
    # Validate configuration before starting
    validate_startup_config()

    if APP_SETTINGS.vectordb:
        try:
            MilvusHelper.initialize()
            logger.info("Milvus connection initialized successfully.")
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Failed to initialize Milvus connection: {str(e)}")
            sys.exit("Failed to initialize Milvus connection. Exiting application.")
        except MilvusConnectionError as e:
            logger.error(f"Milvus connection error: {str(e)}")
            sys.exit("Failed to initialize Milvus connection. Exiting application.")
        except (ValueError, TypeError, AttributeError) as e:
            logger.error(f"Configuration error during Milvus initialization: {str(e)}")
            sys.exit("Failed to initialize Milvus connection. Exiting application.")
        except Exception as e:
            logger.error(f"Unexpected error during Milvus initialization: {str(e)}")
            sys.exit("Failed to initialize Milvus connection. Exiting application.")
    else:
        logger.warning(
            "VectorDB configuration is not set. Skipping Milvus initialization."
        )
        sys.exit("VectorDB configuration is not set. Exiting application.")

    # Start background cleanup task
    import asyncio

    cleanup_task = asyncio.create_task(cleanup_connections())

    yield

    # Cancel cleanup task on shutdown
    cleanup_task.cancel()


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
app.add_middleware(MetricsMiddleware, max_samples=1000, max_endpoints=100)
app.add_middleware(ValidationMiddleware)
app.add_middleware(RequestLoggingMiddleware)

app.include_router(vector.router, prefix="/api/v1/vector_store", tags=["Vector Store"])
app.include_router(
    user.router, prefix="/api/v1/vector_store_users", tags=["User Management"]
)
app.include_router(metrics.router, prefix="/api/v1", tags=["Monitoring"])
app.include_router(health.router, tags=["Health"])


@app.get("/")
def root() -> dict:
    """Root endpoint for health check."""
    return {"message": "Flouds Vector API is running"}


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    """Return empty favicon to prevent 404 errors in browsers."""
    return Response(status_code=204)


def signal_handler(signum: int, frame) -> None:
    """
    Handle shutdown signals gracefully.

    Args:
        signum (int): Signal number received
        frame: Current stack frame (unused)
    """
    logger.info(
        f"Received signal {sanitize_for_log(signum)}, shutting down gracefully..."
    )
    sys.exit(0)


def run_server() -> None:
    """
    Start the FastAPI server with uvicorn.

    Validates configuration, registers signal handlers, and starts the server
    with appropriate settings based on environment.
    """
    # Validate configuration before starting server
    validate_startup_config()

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    logger.info(
        f"Starting server: uvicorn on {sanitize_for_log(APP_SETTINGS.server.host)}:{APP_SETTINGS.server.port}"
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
    except (OSError, PermissionError) as e:
        logger.error(f"Server startup error: {str(e)}")
        sys.exit(1)
    except (ValueError, TypeError, AttributeError) as e:
        logger.error(f"Configuration error: {str(e)}", exc_info=True)
        sys.exit(1)
    except Exception as e:
        logger.error("Fatal error:", exc_info=e)
        sys.exit(1)

# Run Instruction
# Set Env: $env:FLOUDS_API_ENV="Development"
# Unit Test : python -m pytest
# Run for terminal: python -m app.main

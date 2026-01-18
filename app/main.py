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
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from types import FrameType
from typing import Dict, List, Optional

from fastapi import Depends, FastAPI
from fastapi.responses import Response
from fastapi.security import HTTPBearer

from app.app_init import APP_SETTINGS
from app.config.startup_validator import validate_startup_config
from app.dependencies.auth import AuthMiddleware, common_headers
from app.exceptions.custom_exceptions import MilvusConnectionError
from app.logger import get_logger
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.middleware.metrics import MetricsMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_logging import RequestLoggingMiddleware
from app.middleware.tenant_security import (
    TenantCorsMiddleware,
    TenantTrustedHostMiddleware,
)
from app.middleware.validation import ValidationMiddleware
from app.milvus.milvus_helper import MilvusHelper
from app.routers.admin import router as admin_router
from app.routers.config import router as config_router
from app.routers.health import router as health_router
from app.routers.metrics import router as metrics_router
from app.routers.user import router as user_router
from app.routers.vector import router as vector_router
from app.tasks.cleanup import cleanup_connections
from app.milvus.connection_pool import milvus_pool
from app.utils.log_sanitizer import sanitize_for_log

logger = get_logger("main")

API_VERSION = "v1"
API_PREFIX = f"/api/{API_VERSION}"


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

    # Configure bounded default executor for blocking work
    import asyncio

    executor = None
    loop = asyncio.get_running_loop()
    max_workers = APP_SETTINGS.app.default_executor_workers
    if max_workers and max_workers > 0:
        executor = ThreadPoolExecutor(max_workers=max_workers)
        loop.set_default_executor(executor)
        logger.info(
            f"Configured default thread executor with max_workers={sanitize_for_log(max_workers)}"
        )
    else:
        logger.info("Using asyncio default executor (unbounded)")

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
    cleanup_task = asyncio.create_task(cleanup_connections())

    # Initialize security DB and start a small watcher to refresh CORS/trusted hosts
    try:
        from app.services.config_service import config_service

        config_service.init_db()

        # DB-first seeding/override behavior for CORS and Trusted Hosts.
        # If FLOUDS_CONFIG_OVERRIDE=="1", env values overwrite DB at startup.
        # Otherwise, env values only seed the DB when DB has no value.
        from os import getenv

        def _parse_list_env(val: Optional[str]) -> Optional[List[str]]:
            if val is None:
                return None
            if val.strip() == "*":
                return ["*"]
            return [s.strip() for s in val.split(",") if s.strip()]

        cors_env = _parse_list_env(getenv("FLOUDS_CORS_ORIGINS"))
        trusted_env = _parse_list_env(getenv("FLOUDS_TRUSTED_HOSTS"))
        override = getenv("FLOUDS_CONFIG_OVERRIDE") == "1"

        # If override requested, write env -> DB. Otherwise seed DB only when empty.
        try:
            if override:
                if cors_env is not None:
                    config_service.set_cors_origins(cors_env)
                    logger.info("Applied CORS origins from env (override)")
                if trusted_env is not None:
                    config_service.set_trusted_hosts(trusted_env)
                    logger.info("Applied trusted hosts from env (override)")
                config_service.load_and_apply_settings()
            else:
                # Load current DB values to determine if seeding is needed
                existing_cors = config_service.get_cors_origins()
                existing_trusted = config_service.get_trusted_hosts()
                seeded = False
                if (not existing_cors or len(existing_cors) == 0) and cors_env:
                    config_service.set_cors_origins(cors_env)
                    logger.info("Seeded CORS origins from env into DB")
                    seeded = True
                if (not existing_trusted or len(existing_trusted) == 0) and trusted_env:
                    config_service.set_trusted_hosts(trusted_env)
                    logger.info("Seeded trusted hosts from env into DB")
                    seeded = True
                if seeded:
                    config_service.load_and_apply_settings()
                else:
                    # No seeding/override requested — apply whatever is in DB
                    config_service.load_and_apply_settings()
        except Exception:
            logger.exception(
                "Failed to seed/override config from env; falling back to DB values"
            )

        # Caching in `config_service` keeps tenant-scoped CORS and TrustedHost
        # values fresh on writes. Periodic DB polling is no longer required.
    except Exception:
        # Non-fatal: keep app running even if the watcher can't start
        logger.exception("Failed to start security DB watcher; continuing without it")

    yield

    # Cancel cleanup task on shutdown
    cleanup_task.cancel()
    # Close connection pool gracefully
    milvus_pool.close()
    # security_watcher was removed; caching invalidation handles updates.
    if executor:
        executor.shutdown(wait=False)


app = FastAPI(
    title="Flouds Vector API",
    description="Multi-tenant vector database API with Milvus backend",
    version="1.0.0",
    openapi_url=f"{API_PREFIX}/openapi.json",
    docs_url=f"{API_PREFIX}/docs",
    redoc_url=f"{API_PREFIX}/redoc",
    lifespan=lifespan,
    # Keep a non-blocking HTTPBearer at app-level so the OpenAPI "Authorize"
    # control is available, but don't add `common_headers` here because it
    # injects header parameters into every endpoint (including public ones
    # like `/health`). Attach `common_headers` only to secured routers below.
    dependencies=[Depends(HTTPBearer(auto_error=False))],
)
# Configure and add middleware
# Use tenant-aware middleware for CORS and Trusted Host enforcement
# Register CORS first so browser preflight and CORS headers are handled
# before TrustedHost enforces server-side host restrictions. This ensures
# browsers receive correct CORS responses while trusted-host remains a
# server-side safety net.
app.add_middleware(TenantCorsMiddleware)
app.add_middleware(TenantTrustedHostMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(RateLimitMiddleware, calls=100, period=60)
app.add_middleware(MetricsMiddleware, max_samples=1000, max_endpoints=100)
app.add_middleware(ValidationMiddleware)
app.add_middleware(RequestLoggingMiddleware)

app.include_router(
    vector_router,
    prefix=f"{API_PREFIX}/vector_store",
    tags=["Vector Store"],
    dependencies=[Depends(common_headers)],
)
app.include_router(
    user_router,
    prefix=f"{API_PREFIX}/vector_store_users",
    tags=["User Management"],
    dependencies=[Depends(common_headers)],
)
app.include_router(metrics_router, prefix=API_PREFIX, tags=["Monitoring"])
app.include_router(health_router, prefix=API_PREFIX, tags=["Health"])
app.include_router(
    admin_router,
    prefix=f"{API_PREFIX}/admin",
    tags=["Admin"],
    dependencies=[Depends(common_headers)],
)
app.include_router(
    config_router,
    prefix=f"{API_PREFIX}/config",
    tags=["Config"],
    dependencies=[Depends(common_headers)],
)


@app.get("/")
def root() -> Dict[str, str]:
    """Root endpoint for health check."""
    return {"message": "Flouds Vector API is running"}


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    """Return empty favicon to prevent 404 errors in browsers."""
    return Response(status_code=204)


def signal_handler(signum: int, frame: Optional[FrameType]) -> None:
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

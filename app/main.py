# =============================================================================
# File: main.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import asyncio
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.app_init import APP_SETTINGS
from app.milvus.milvus_helper import MilvusHelper
from app.routers import user, vector_store

logger = logging.getLogger("main")


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


app = FastAPI(lifespan=lifespan)
app.include_router(vector_store.router)
app.include_router(user.router)


@app.get("/")
def root() -> dict:
    """Root endpoint for health check."""
    return {"message": "FloudsVectors.Py API is running"}


def run_server():
    logger.info(
        f"Starting server: {APP_SETTINGS.server.type} on {APP_SETTINGS.server.host}:{APP_SETTINGS.server.port}"
    )
    server_type = APP_SETTINGS.server.type.lower()
    if server_type == "hypercorn":
        try:
            from hypercorn.asyncio import serve
            from hypercorn.config import Config
        except ImportError:
            logger.error(
                "hypercorn is not installed. Please install it to use this server type."
            )
            raise

        config = Config()
        config.bind = [f"{APP_SETTINGS.server.host}:{APP_SETTINGS.server.port}"]
        config.workers = APP_SETTINGS.server.workers
        config.reload = APP_SETTINGS.server.reload

        asyncio.run(serve(app, config))
    else:
        import uvicorn

        uvicorn.run(
            app,
            host=APP_SETTINGS.server.host,
            port=APP_SETTINGS.server.port,
            reload=APP_SETTINGS.server.reload,
            workers=APP_SETTINGS.server.workers,
        )


if __name__ == "__main__":
    run_server()

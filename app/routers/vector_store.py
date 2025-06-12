# =============================================================================
# File: embedder.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import asyncio

from fastapi import APIRouter

from app.logger import get_logger
from app.models.database_info import DatabaseInfoResponse
from app.models.set_vector_store_request import SetVectorStoreRequest
from app.services.vector_store_service import VectorStoreService

router = APIRouter()
logger = get_logger("router")


@router.post("/set_or_get", tags=["vector_store"], response_model=DatabaseInfoResponse)
async def set_or_get(request: SetVectorStoreRequest) -> DatabaseInfoResponse:
    logger.debug(f"Vector store request by model: {request.for_tenant}")
    response: DatabaseInfoResponse = await asyncio.to_thread(
        VectorStoreService.set_vector_store, request
    )
    logger.debug(f"Vector store response: {response.for_tenant} - {response.success}")
    if not response.success:
        logger.error(f"Error in vector store operation: {response.message}")
    else:
        logger.info(
            f"Vector store operation successful for tenant: {response.for_tenant}"
        )
    return response

# =============================================================================
# File: user.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import asyncio

from fastapi import APIRouter
from fastapi import Depends

from app.dependencies.auth import get_token
from app.logger import get_logger
from app.models.base_request import BaseRequest
from app.models.list_response import ListResponse
from app.services.vector_store_service import VectorStoreService
from app.utils.common_utils import CommonUtils

router = APIRouter()
logger = get_logger("router")


@router.post("/set", tags=["vector_store_users"], response_model=ListResponse)
async def set_user(request: BaseRequest, token: str = Depends(get_token)) -> ListResponse:
    """
    Sets a user in the vector store for the given tenant.

    Args:
        request (BaseRequest): The request object containing tenant and token info.

    Returns:
        ListResponse: The response with operation details.
    """
    logger.debug(f"Vector store request set user for tenant: {request.tenant_code}")
    response: ListResponse = await asyncio.to_thread(
        VectorStoreService.set_user,
        request,
        token=token,
        **CommonUtils.parse_extra_fields(request, BaseRequest),
    )
    logger.debug(f"Vector store response: {response.for_tenant} - {response.success}")
    if not response.success:
        logger.error(f"Error in vector store operation: {response.message}")
    else:
        logger.info(
            f"Vector store operation successful for tenant: {response.for_tenant}"
        )
    return response

# =============================================================================
# File: vector_store.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import asyncio

from fastapi import APIRouter
from fastapi import Depends

from app.dependencies.auth import get_token
from app.logger import get_logger
from app.models.base_response import BaseResponse
from app.models.insert_request import InsertEmbeddedRequest
from app.models.list_response import ListResponse
from app.models.search_request import SearchEmbeddedRequest
from app.models.search_response import SearchEmbeddedResponse
from app.models.set_vector_store_request import SetVectorStoreRequest
from app.services.vector_store_service import VectorStoreService
from app.utils.common_utils import CommonUtils

router: APIRouter = APIRouter()
logger = get_logger("router")


@router.post("/set_vector_store", tags=["vector_store"], response_model=ListResponse)
async def set_vector_store(request: SetVectorStoreRequest, token: str = Depends(get_token)) -> ListResponse:
    """
    Sets or retrieves a vector store for the given tenant.

    Args:
        request (SetVectorStoreRequest): The request object with tenant, token, and vector dimension.

    Returns:
        ListResponse: The response with vector store details.
    """
    logger.debug(f"Vector store request set_vector_store for tenant: {request.tenant_code}")
    response: ListResponse = await asyncio.to_thread(
        VectorStoreService.set_vector_store,
        request,
        token=token,
        **CommonUtils.parse_extra_fields(request, SetVectorStoreRequest),
    )
    logger.debug(f"Vector store response: {response.for_tenant} - {response.success}")
    if not response.success:
        logger.error(f"Error in vector store operation: {response.message}")
    else:
        logger.info(
            f"Vector store operation successful for tenant: {response.for_tenant}"
        )
    return response


@router.post("/insert", tags=["vector_store"], response_model=BaseResponse)
async def insert(request: InsertEmbeddedRequest, token: str = Depends(get_token)) -> BaseResponse:
    """
    Inserts embedded vectors into the vector store for the given tenant.

    Args:
        request (InsertEmbeddedRequest): The request object with tenant, token, and data.

    Returns:
        BaseResponse: The response with insertion details.
    """
    logger.debug(f"Vector store request insert for tenant: {request.tenant_code}")
    response: BaseResponse = await asyncio.to_thread(
        VectorStoreService.insert_into_vector_store,
        request,
        token=token,
        **CommonUtils.parse_extra_fields(request, InsertEmbeddedRequest),
    )
    logger.debug(f"Vector store response: {response.for_tenant} - {response.success}")
    if not response.success:
        logger.error(f"Error in vector store operation: {response.message}")
    else:
        logger.info(
            f"Vector store operation successful for tenant: {response.for_tenant}"
        )
    return response


@router.post("/search", tags=["vector_store"], response_model=SearchEmbeddedResponse)
async def search(
    request: SearchEmbeddedRequest,
    token: str = Depends(get_token)
) -> SearchEmbeddedResponse:
    """
    Searches for embedded vectors in the vector store for the given tenant.

    Args:
        request (SearchEmbeddedRequest): The request object with tenant, token, and search parameters.

    Returns:
        BaseResponse: The response with search details.
    """
    logger.debug(f"Vector store request search for tenant: {request.tenant_code}")
    response: SearchEmbeddedResponse = await asyncio.to_thread(
        VectorStoreService.search_in_vector_store,
        request,
        token=token,
        **CommonUtils.parse_extra_fields(request, SearchEmbeddedRequest),
    )
    logger.debug(f"Vector store response: {response.for_tenant} - {response.success}")
    if not response.success:
        logger.error(f"Error in vector store operation: {response.message}")
    else:
        logger.info(
            f"Vector store operation successful for tenant: {response.for_tenant}"
        )
    return response

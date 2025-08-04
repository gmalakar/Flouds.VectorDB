# =============================================================================
# File: vector.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import asyncio

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.dependencies.auth import get_token
from app.logger import get_logger
from app.middleware.tenant_rate_limit import check_tenant_rate_limit
from app.models.base_response import BaseResponse
from app.models.generate_schema_request import GenerateSchemaRequest
from app.models.insert_request import InsertEmbeddedRequest
from app.models.list_response import ListResponse
from app.models.search_request import SearchEmbeddedRequest
from app.models.search_response import SearchEmbeddedResponse
from app.models.set_vector_store_request import SetVectorStoreRequest
from app.services.vector_store_service import VectorStoreService
from app.utils.common_utils import CommonUtils
from app.utils.log_sanitizer import sanitize_for_log

router: APIRouter = APIRouter()
logger = get_logger("router")


def log_response(response, operation: str):
    """
    Logs the response for a given operation with sanitization.
    """
    tenant_code = sanitize_for_log(response.tenant_code)
    success = response.success

    logger.debug(f"{operation} response: {tenant_code} - {success}")

    if not success:
        error_msg = sanitize_for_log(response.message)
        logger.error(f"Error in {operation}: {error_msg}")
    else:
        logger.info(f"{operation} successful for tenant: {tenant_code}")

        if hasattr(response, "results") and response.results:
            result_keys = (
                list(response.results.keys())
                if isinstance(response.results, dict)
                else "[data]"
            )
            logger.debug(f"{operation} response contains: {result_keys}")


@router.post("/set_vector_store", response_model=ListResponse)
async def set_vector_store(
    request: SetVectorStoreRequest,
    token: str = Depends(get_token),
    _: None = Depends(
        lambda r=None: check_tenant_rate_limit(r.tenant_code if r else "")
    ),
) -> ListResponse:
    """
    Sets up database, user, and permissions for the given tenant.
    Does NOT create collections or indexes - use generate_schema for that.

    Args:
        request (SetVectorStoreRequest): The request object with tenant, token, and vector dimension.

    Returns:
        ListResponse: The response with tenant setup details.
    """
    logger.debug(
        f"set_vector_store request for tenant: {sanitize_for_log(request.tenant_code)}"
    )
    extra_fields = CommonUtils.parse_extra_fields(request, SetVectorStoreRequest)
    response: ListResponse = await asyncio.to_thread(
        VectorStoreService.set_vector_store, request, token=token, **extra_fields
    )
    log_response(response, "set_vector_store")
    return response


@router.post("/insert", response_model=BaseResponse)
async def insert(
    request: InsertEmbeddedRequest,
    token: str = Depends(get_token),
    _: None = Depends(
        lambda r=None: check_tenant_rate_limit(r.tenant_code if r else "")
    ),
) -> BaseResponse:
    """
    Inserts embedded vectors into the model-specific collection for the given tenant.
    All vectors must use the same model name.

    Args:
        request (InsertEmbeddedRequest): The request object with tenant, token, and data.

    Returns:
        BaseResponse: The response with insertion details.
    """
    logger.debug(
        f"insert request for tenant: {sanitize_for_log(request.tenant_code)}, vectors: {len(request.data)}"
    )
    extra_fields = CommonUtils.parse_extra_fields(request, InsertEmbeddedRequest)
    response: BaseResponse = await asyncio.to_thread(
        VectorStoreService.insert_into_vector_store,
        request,
        token=token,
        **extra_fields,
    )
    log_response(response, "insert")
    return response


@router.post("/search", response_model=SearchEmbeddedResponse)
async def search(
    request: SearchEmbeddedRequest,
    token: str = Depends(get_token),
    _: None = Depends(
        lambda r=None: check_tenant_rate_limit(r.tenant_code if r else "")
    ),
) -> SearchEmbeddedResponse:
    """
    Searches for embedded vectors in the model-specific collection for the given tenant.
    Uses the model field to determine which collection to search.

    Args:
        request (SearchEmbeddedRequest): The request object with tenant, token, model, and search parameters.

    Returns:
        SearchEmbeddedResponse: The response with search details.
    """
    logger.debug(
        f"search request for tenant: {sanitize_for_log(request.tenant_code)}, limit: {request.limit}"
    )
    extra_fields = CommonUtils.parse_extra_fields(request, SearchEmbeddedRequest)
    response: SearchEmbeddedResponse = await asyncio.to_thread(
        VectorStoreService.search_in_vector_store,
        request,
        token=token,
        **extra_fields,
    )
    log_response(response, "search")
    return response


@router.post("/generate_schema", response_model=ListResponse)
async def generate_schema(
    request: GenerateSchemaRequest,
    token: str = Depends(get_token),
    _: None = Depends(
        lambda r=None: check_tenant_rate_limit(r.tenant_code if r else "")
    ),
) -> ListResponse:
    """
    Generates a custom schema for the given tenant with specified parameters.

    Args:
        request (GenerateSchemaRequest): The request object with tenant, model, and schema parameters.

    Returns:
        ListResponse: The response with schema generation details.
    """
    logger.debug(
        f"generate_schema request for tenant: {sanitize_for_log(request.tenant_code)}, model: {sanitize_for_log(request.model_name)}, dimension: {request.dimension}"
    )
    extra_fields = CommonUtils.parse_extra_fields(request, GenerateSchemaRequest)
    response: ListResponse = await asyncio.to_thread(
        VectorStoreService.generate_schema, request, token=token, **extra_fields
    )
    log_response(response, "generate_schema")
    return response


@router.post("/flush", response_model=BaseResponse)
async def flush_collection(
    tenant_code: str,
    model_name: str,
    token: str = Depends(get_token),
    _: None = Depends(lambda: check_tenant_rate_limit(tenant_code)),
) -> BaseResponse:
    """
    Manually flush a tenant's collection for immediate data persistence.
    Useful after batch operations with deferred flushing.
    """
    logger.debug(
        f"flush request for tenant: {sanitize_for_log(tenant_code)}, model: {sanitize_for_log(model_name)}"
    )
    response: BaseResponse = await asyncio.to_thread(
        VectorStoreService.flush_vector_store,
        tenant_code=tenant_code,
        model_name=model_name,
        token=token,
    )
    log_response(response, "flush")
    return response

# =============================================================================
# File: user.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import asyncio

from fastapi import APIRouter, Depends

from app.dependencies.auth import get_token
from app.logger import get_logger
from app.models.list_response import ListResponse
from app.models.reset_password_request import ResetPasswordRequest
from app.models.reset_password_response import ResetPasswordResponse
from app.models.set_user_request import SetUserRequest
from app.services.vector_store_service import VectorStoreService
from app.utils.common_utils import CommonUtils

router = APIRouter()
logger = get_logger("router")


@router.post("/set_user", tags=["vector-store-users"], response_model=ListResponse)
async def set_user(
    request: SetUserRequest, token: str = Depends(get_token)
) -> ListResponse:
    """
    Sets a user in the vector store for the given tenant.

    Args:
        request (SetUserRequest): The request object containing tenant and token info.

    Returns:
        ListResponse: The response with operation details.
    """
    logger.debug(f"Vector store request set user for tenant: {request.tenant_code}")
    response: ListResponse = await asyncio.to_thread(
        VectorStoreService.set_user,
        request,
        token=token,
        **CommonUtils.parse_extra_fields(request, SetUserRequest),
    )
    logger.debug(f"Vector store response: {response.tenant_code} - {response.success}")
    if not response.success:
        logger.error(f"Error in vector store operation: {response.message}")
    else:
        logger.info(
            f"Vector store operation successful for tenant: {response.tenant_code}"
        )
    return response


@router.post(
    "/reset_password", tags=["vector-store-users"], response_model=ResetPasswordResponse
)
async def reset_password(
    request: ResetPasswordRequest, token: str = Depends(get_token)
) -> ResetPasswordResponse:
    """
    Resets a user in the vector store for the given tenant.

    Args:
        request (ResetPasswordRequest): The request object containing tenant and token info.

    Returns:
        ListResponse: The response with operation details.
    """
    logger.debug(
        f"Vector store request reset password for tenant: {request.tenant_code}"
    )
    response: ResetPasswordResponse = await asyncio.to_thread(
        VectorStoreService.reset_password,
        request,
        token=token,
        **CommonUtils.parse_extra_fields(request, ResetPasswordRequest),
    )
    logger.debug(f"Vector store response: {response.tenant_code} - {response.success}")
    if not response.success:
        logger.error(f"Error in vector store operation: {response.message}")
    else:
        logger.info(
            f"Vector store operation successful for tenant: {response.tenant_code}"
        )
    return response

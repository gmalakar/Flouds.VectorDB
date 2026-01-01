# =============================================================================
# File: user.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import asyncio

from fastapi import APIRouter, Depends, Request

from app.dependencies.auth import get_db_token
from app.logger import get_logger
from app.models.list_response import ListResponse
from app.models.reset_password_request import ResetPasswordRequest
from app.models.reset_password_response import ResetPasswordResponse
from app.models.set_user_request import SetUserRequest
from app.services.vector_store_service import VectorStoreService
from app.utils.common_utils import CommonUtils
from app.utils.log_sanitizer import sanitize_for_log

router = APIRouter()
logger = get_logger("router")


def log_response(response, operation: str) -> None:
    """
    Logs the response for a given operation.

    Args:
        response: The response object to log.
        operation (str): The operation name.
    """
    logger.debug(
        f"{operation} response: {sanitize_for_log(response.tenant_code)} - {response.success}"
    )
    if not response.success:
        logger.error(f"Error in {operation}: {response.message}")
    else:
        logger.info(
            f"{operation} successful for tenant: {sanitize_for_log(response.tenant_code)}"
        )


@router.post("/set_user", response_model=ListResponse)
async def set_user(
    request: SetUserRequest,
    http_request: Request,
    db_secret: str = Depends(get_db_token),
) -> ListResponse:
    """
    Sets a user in the vector store for the given tenant.
    Requires `Flouds-VectorDB-Token` header for database credentials.

    Args:
        request (SetUserRequest): The request object containing tenant and token info.
        http_request (Request): FastAPI request to access authenticated client info.

    Returns:
        ListResponse: The response with operation details.
    """
    logger.debug(
        f"set_user request for tenant: {sanitize_for_log(request.tenant_code)}"
    )

    extra_fields = CommonUtils.parse_extra_fields(request, SetUserRequest)
    response: ListResponse = await asyncio.to_thread(
        VectorStoreService.set_user,
        request,
        token=db_secret,
        **extra_fields,
    )
    log_response(response, "set_user")
    return response


@router.post("/reset_password", response_model=ResetPasswordResponse)
async def reset_password(
    request: ResetPasswordRequest,
    http_request: Request,
    db_secret: str = Depends(get_db_token),
) -> ResetPasswordResponse:
    """
    Resets a user in the vector store for the given tenant.
    Requires `Flouds-VectorDB-Token` header for database credentials.

    Args:
        request (ResetPasswordRequest): The request object containing tenant and token info.
        http_request (Request): FastAPI request to access authenticated client info.

    Returns:
        ResetPasswordResponse: The response with operation details.
    """
    logger.debug(
        f"reset_password request for tenant: {sanitize_for_log(request.tenant_code)}"
    )

    extra_fields = CommonUtils.parse_extra_fields(request, ResetPasswordRequest)
    response: ResetPasswordResponse = await asyncio.to_thread(
        VectorStoreService.reset_password,
        request,
        token=db_secret,
        **extra_fields,
    )
    log_response(response, "reset_password")
    return response

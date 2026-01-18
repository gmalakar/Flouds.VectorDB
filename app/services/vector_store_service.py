# =============================================================================
# File: vector_store_service.py
# Description: Service layer for vector store operations including CRUD and search
# Author: Goutam Malakar
# Date: 2025-01-15
# Version: 1.0.0
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================


import re
from functools import wraps
from time import time
from typing import Any, Callable, Tuple, TypeVar, Union, cast

from app.exceptions.custom_exceptions import (
    AuthenticationError,
    MilvusOperationError,
    SearchError,
    UserManagementError,
    ValidationError,
    VectorStoreError,
)
from app.logger import get_logger
from app.milvus.milvus_helper import MilvusHelper
from app.models.base_response import BaseResponse
from app.models.generate_schema_request import GenerateSchemaRequest
from app.models.insert_request import InsertEmbeddedRequest
from app.models.list_response import ListResponse
from app.models.reset_password_request import ResetPasswordRequest
from app.models.reset_password_response import ResetPasswordResponse
from app.models.search_request import SearchEmbeddedRequest
from app.models.search_response import SearchEmbeddedResponse
from app.models.set_user_request import SetUserRequest
from app.models.set_vector_store_request import SetVectorStoreRequest
from app.utils.log_sanitizer import sanitize_for_log

logger = get_logger("vector_store_service")

T = TypeVar("T")


# Exception handler mapping for service methods
# Maps exception types to (message_template, log_message) tuples
_SERVICE_EXCEPTION_HANDLERS = {
    UserManagementError: (
        "User management error: {}",
        "User management error during operation",
    ),
    MilvusOperationError: (
        "Database operation error: {}",
        "Database error during operation",
    ),
    VectorStoreError: ("Vector store error: {}", "Vector store error during operation"),
    SearchError: ("Search error: {}", "Search error during operation"),
    ValidationError: ("Validation error: {}", "Validation error during operation"),
    AuthenticationError: (
        "Database token error: {}",
        "Authentication error during operation",
    ),
    ValueError: ("Invalid data: {}", "Data validation error during operation"),
}


def _handle_service_exception(response: Any, exc: Exception) -> None:
    """
    Handle exceptions in service methods using centralized exception mapping.

    Args:
        response: The response object to update with error details.
        exc: The exception that occurred.
    """
    response.success = False

    # Check for known exception types
    for exc_type, (msg_template, log_msg) in _SERVICE_EXCEPTION_HANDLERS.items():
        if isinstance(exc, exc_type):
            response.message = msg_template.format(str(exc))
            logger.exception(log_msg)
            return

    # Generic fallback for unexpected exceptions
    response.message = f"Unexpected error: {str(exc)}"
    logger.exception("Unexpected error during operation")


def service_method(
    default_response_factory: Callable[..., Any],
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator for timing, error handling, and logging in service methods.

    Expects the wrapped function to return (response, main_logic), where main_logic is a callable.

    Args:
        default_response_factory (Callable[..., T]): Factory to create a default response object.

    Returns:
        Callable: Decorated function with error handling and timing.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time()
            returned = func(*args, **kwargs)
            if isinstance(returned, tuple) and len(returned) == 2:
                response, main_logic = returned  # type: ignore[list-item]
            else:
                response = returned  # type: ignore[assignment]
                main_logic = lambda r: r  # type: ignore[assignment]
            response_any = cast(Any, response)
            try:
                return_value = main_logic(response)
            except Exception as e:
                _handle_service_exception(response_any, e)
            finally:
                response_any.time_taken = time() - start_time
                logger.debug(
                    f"{func.__name__} completed in {response_any.time_taken:.2f} seconds."
                )
                return response_any

        return cast(Callable[..., Any], wrapper)

    return decorator


class VectorStoreService:
    """
    Service class for vector store operations.

    Provides high-level business logic for vector store management including
    user management, tenant setup, data insertion, and similarity search.
    All methods are class methods for stateless operation.
    """

    @classmethod
    @service_method(
        lambda request, **_: ListResponse(
            tenant_code=request.tenant_code,
            success=True,
            message="User set successfully.",
            time_taken=0.0,
            results={},
        )
    )
    def set_user(
        cls, request: SetUserRequest, token: str, **kwargs: Any
    ) -> Union[
        ListResponse, Tuple[ListResponse, Callable[[ListResponse], ListResponse]]
    ]:
        """
        Set a user in the vector store.

        Args:
            request (SetUserRequest): The user request object.
            token (str): Authentication token.
            **kwargs: Additional keyword arguments.

        Returns:
            ListResponse: Response object with operation result.
        """

        def main_logic(response: ListResponse):
            logger.debug(
                f"User set request: {sanitize_for_log(request.tenant_code)}, kwargs: {kwargs}"
            )
            response.results = MilvusHelper.set_user(
                request=request, token=token, **kwargs
            )
            response.message = response.results.get("message", "User set successfully.")
            return response

        return (
            ListResponse(
                tenant_code=request.tenant_code,
                success=True,
                message="User set successfully.",
                time_taken=0.0,
                results={},
            ),
            main_logic,
        )

    @classmethod
    @service_method(
        lambda request, **_: ResetPasswordResponse(
            tenant_code=request.tenant_code,
            user_name=request.user_name,
            success=False,
            message="Password reset failed.",
            time_taken=0.0,
            root_user=False,
            reset_flag=False,
            results={},
        )
    )
    def reset_password(
        cls, request: ResetPasswordRequest, token: str, **kwargs: Any
    ) -> Union[
        ResetPasswordResponse,
        Tuple[
            ResetPasswordResponse,
            Callable[[ResetPasswordResponse], ResetPasswordResponse],
        ],
    ]:
        """
        Reset a user's password in the vector store.

        Args:
            request (ResetPasswordRequest): The password reset request.
            token (str): Authentication token.
            **kwargs: Additional keyword arguments.

        Returns:
            ResetPasswordResponse: Response object with operation result.
        """

        def main_logic(response: ResetPasswordResponse):
            logger.debug(
                f"Password reset request: {sanitize_for_log(request.tenant_code)}, kwargs: {kwargs}"
            )
            resp2 = MilvusHelper.reset_password(request=request, token=token, **kwargs)
            response.message = resp2.message
            response.root_user = resp2.root_user
            response.success = resp2.success
            response.reset_flag = resp2.reset_flag
            return response

        return (
            ResetPasswordResponse(
                tenant_code=request.tenant_code,
                user_name=request.user_name,
                success=False,
                message="Password reset failed.",
                time_taken=0.0,
                root_user=False,
                reset_flag=False,
                results={},
            ),
            main_logic,
        )

    @classmethod
    @service_method(
        lambda requests, **_: ListResponse(
            tenant_code=requests.tenant_code,
            success=True,
            message="Tenant setup completed successfully.",
            results={},
            time_taken=0.0,
        )
    )
    def set_vector_store(
        cls, requests: SetVectorStoreRequest, token: str, **kwargs: Any
    ) -> Union[
        ListResponse, Tuple[ListResponse, Callable[[ListResponse], ListResponse]]
    ]:
        """
        Set up a vector store for a tenant.

        Args:
            requests (SetVectorStoreRequest): The vector store setup request.
            token (str): Authentication token.
            **kwargs: Additional keyword arguments.

        Returns:
            ListResponse: Response object with operation result.
        """

        def main_logic(response: ListResponse):
            logger.debug(f"set_vector_store: kwargs received: {kwargs}")
            response.results = MilvusHelper.set_vector_store(
                tenant_code=(requests.tenant_code or ""), token=token, **kwargs
            )
            return response

        return (
            ListResponse(
                tenant_code=requests.tenant_code,
                success=True,
                message="Tenant setup completed successfully.",
                results={},
                time_taken=0.0,
            ),
            main_logic,
        )

    @classmethod
    @service_method(
        lambda requests, **_: BaseResponse(
            tenant_code=requests.tenant_code,
            success=True,
            message="Vector store inserted successfully.",
            time_taken=0.0,
            results={},
        )
    )
    def insert_into_vector_store(
        cls, requests: InsertEmbeddedRequest, token: str, **kwargs: Any
    ) -> Union[
        BaseResponse, Tuple[BaseResponse, Callable[[BaseResponse], BaseResponse]]
    ]:
        """
        Insert data into the vector store.

        Args:
            requests (InsertEmbeddedRequest): The data insertion request.
            token (str): Authentication token.
            **kwargs: Additional keyword arguments.

        Returns:
            BaseResponse: Response object with operation result.
        """

        def main_logic(response: BaseResponse):
            logger.debug(f"Insert request: {sanitize_for_log(requests.tenant_code)}")
            num_inserted = MilvusHelper.insert_embedded_data(
                request=requests, token=token, **kwargs
            )
            batch_size = len(requests.data)
            flush_status = (
                "auto-flushed"
                if batch_size >= 100 or kwargs.get("force_flush")
                else "deferred"
            )
            response.message = f"Vector store inserted successfully. {num_inserted} vectors inserted ({flush_status})."
            return response

        return (
            BaseResponse(
                tenant_code=requests.tenant_code,
                success=True,
                message="Vector store inserted successfully.",
                time_taken=0.0,
                results={},
            ),
            main_logic,
        )

    @classmethod
    @service_method(
        lambda tenant_code, model_name, token, **_: BaseResponse(
            tenant_code=tenant_code,
            success=True,
            message="Collection flushed successfully.",
            time_taken=0.0,
            results={},
        )
    )
    def flush_vector_store(
        cls, tenant_code: str, model_name: str, token: str
    ) -> Union[
        BaseResponse, Tuple[BaseResponse, Callable[[BaseResponse], BaseResponse]]
    ]:
        """
        Flush a tenant's collection in the vector store.

        Args:
            tenant_code (str): The tenant code.
            model_name (str): The model name.
            token (str): Authentication token.

        Returns:
            BaseResponse: Response object with operation result.
        """

        def main_logic(response: BaseResponse):
            success = MilvusHelper.flush_tenant_collection(
                tenant_code=tenant_code, model_name=model_name, token=token
            )
            if not success:
                response.success = False
                response.message = "Failed to flush collection."
            return response

        return (
            BaseResponse(
                tenant_code=tenant_code,
                success=True,
                message="Collection flushed successfully.",
                time_taken=0.0,
                results={},
            ),
            main_logic,
        )

    @classmethod
    @service_method(
        lambda requests, token, **_: SearchEmbeddedResponse(
            tenant_code=requests.tenant_code,
            model=requests.model,
            limit=requests.limit,
            offset=requests.offset,
            nprobe=requests.nprobe,
            round_decimal=requests.round_decimal,
            consistency_level=requests.consistency_level,
            output_fields=requests.output_fields,
            score_threshold=requests.score_threshold,
            meta_required=requests.meta_required,
            metric_type=requests.metric_type,
            text_filter=requests.text_filter,
            minimum_words_match=requests.minimum_words_match,
            include_stop_words=requests.include_stop_words,
            increase_limit_for_text_search=requests.increase_limit_for_text_search,
            hybrid_search=requests.hybrid_search,
            success=True,
            message="Vector store search completed successfully.",
            time_taken=0.0,
            data=[],
            results={},
        )
    )
    def search_in_vector_store(
        cls, requests: SearchEmbeddedRequest, token: str, **kwargs: Any
    ) -> Union[
        SearchEmbeddedResponse,
        Tuple[
            SearchEmbeddedResponse,
            Callable[[SearchEmbeddedResponse], SearchEmbeddedResponse],
        ],
    ]:
        """
        Search for vectors in the vector store.

        Args:
            requests (SearchEmbeddedRequest): The search request.
            token (str): Authentication token.
            **kwargs: Additional keyword arguments.

        Returns:
            SearchEmbeddedResponse: Response object with search results.
        """

        def main_logic(response: SearchEmbeddedResponse):
            logger.debug(f"Search request: {sanitize_for_log(requests.tenant_code)}")
            search_results = MilvusHelper.search_embedded_data(
                request=requests, token=token, **kwargs
            )
            response.data = search_results
            if not search_results:
                response.success = False
                response.message = "No vectors found in the vector store."
            return response

        return (
            SearchEmbeddedResponse(
                tenant_code=requests.tenant_code,
                model=requests.model,
                limit=requests.limit,
                offset=requests.offset,
                nprobe=requests.nprobe,
                round_decimal=requests.round_decimal,
                consistency_level=requests.consistency_level,
                output_fields=requests.output_fields,
                score_threshold=requests.score_threshold,
                meta_required=requests.meta_required,
                metric_type=requests.metric_type,
                text_filter=requests.text_filter,
                minimum_words_match=requests.minimum_words_match,
                include_stop_words=requests.include_stop_words,
                increase_limit_for_text_search=requests.increase_limit_for_text_search,
                hybrid_search=requests.hybrid_search,
                success=True,
                message="Vector store search completed successfully.",
                time_taken=0.0,
                data=[],
                results={},
            ),
            main_logic,
        )

    @classmethod
    @service_method(
        lambda request, token, **_: ListResponse(
            tenant_code=request.tenant_code,
            success=True,
            message="Custom schema generated successfully.",
            results={},
            time_taken=0.0,
        )
    )
    def generate_schema(
        cls, request: GenerateSchemaRequest, token: str, **kwargs: Any
    ) -> Union[
        ListResponse, Tuple[ListResponse, Callable[[ListResponse], ListResponse]]
    ]:
        """
        Generate a custom schema for a tenant's collection.

        Args:
            request (GenerateSchemaRequest): The schema generation request.
            token (str): Authentication token.
            **kwargs: Additional keyword arguments.

        Returns:
            ListResponse: Response object with operation result.
        """

        def main_logic(response: ListResponse):
            logger.debug(
                f"Generate schema request: {sanitize_for_log(request.tenant_code)}, model_name: {sanitize_for_log(request.model_name)}"
            )
            response.results = MilvusHelper.generate_schema(
                tenant_code=(request.tenant_code or ""),
                model_name=request.model_name,
                dimension=request.dimension,
                nlist=request.nlist,
                metric_type=request.metric_type,
                index_type=request.index_type,
                metadata_length=request.metadata_length,
                drop_ratio_build=request.drop_ratio_build,
                token=token,
                **kwargs,
            )
            response.message = response.results.get(
                "message", "Custom schema generated successfully."
            )
            return response

        return (
            ListResponse(
                tenant_code=request.tenant_code,
                success=True,
                message="Custom schema generated successfully.",
                results={},
                time_taken=0.0,
            ),
            main_logic,
        )

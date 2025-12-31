# =============================================================================
# File: vector_store_service.py
# Description: Service layer for vector store operations including CRUD and search
# Author: Goutam Malakar
# Date: 2025-01-15
# Version: 1.0.0
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================


import re
from time import time
from typing import Any, Callable, TypeVar, cast
from functools import wraps

from app.exceptions.custom_exceptions import (
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

def service_method(default_response_factory: Callable[..., T]):
    """
    Decorator for timing, error handling, and logging in service methods.
    Expects the wrapped function to return (response, main_logic), where main_logic is a callable.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            start_time = time()
            response, main_logic = func(*args, **kwargs)
            try:
                return_value = main_logic(response)
            except UserManagementError as e:
                response.success = False
                response.message = f"User management error: {str(e)}"
                logger.exception("User management error during operation")
            except MilvusOperationError as e:
                response.success = False
                response.message = f"Database operation error: {str(e)}"
                logger.exception("Database error during operation")
            except VectorStoreError as e:
                response.success = False
                response.message = f"Vector store error: {str(e)}"
                logger.exception("Vector store error during operation")
            except SearchError as e:
                response.success = False
                response.message = f"Search error: {str(e)}"
                logger.exception("Search error during operation")
            except ValidationError as e:
                response.success = False
                response.message = f"Validation error: {str(e)}"
                logger.exception("Validation error during operation")
            except ValueError as e:
                response.success = False
                response.message = f"Invalid data: {str(e)}"
                logger.exception("Data validation error during operation")
            except Exception as e:
                response.success = False
                response.message = f"Unexpected error: {str(e)}"
                logger.exception("Unexpected error during operation")
            finally:
                response.time_taken = time() - start_time
                logger.debug(f"{func.__name__} completed in {response.time_taken:.2f} seconds.")
                return response
        return cast(Callable[..., T], wrapper)
    return decorator


class VectorStoreService:
    """
    Service class for vector store operations.

    Provides high-level business logic for vector store management including
    user management, tenant setup, data insertion, and similarity search.
    All methods are class methods for stateless operation.
    """

    @classmethod
    @service_method(lambda request, **_: ListResponse(tenant_code=request.tenant_code, success=True, message="User set successfully.", time_taken=0.0, results={}))
    def set_user(cls, request: SetUserRequest, token: str, **kwargs: Any):
        def main_logic(response: ListResponse):
            logger.debug(f"User set request: {sanitize_for_log(request.tenant_code)}, kwargs: {kwargs}")
            response.results = MilvusHelper.set_user(request=request, token=token, **kwargs)
            response.message = response.results.get("message", "User set successfully.")
            return response
        return ListResponse(tenant_code=request.tenant_code, success=True, message="User set successfully.", time_taken=0.0, results={}), main_logic

    @classmethod
    @service_method(lambda request, **_: ResetPasswordResponse(tenant_code=request.tenant_code, user_name=request.user_name, success=False, message="Password reset failed.", time_taken=0.0))
    def reset_password(cls, request: ResetPasswordRequest, token: str, **kwargs: Any):
        def main_logic(response: ResetPasswordResponse):
            logger.debug(f"Password reset request: {sanitize_for_log(request.tenant_code)}, kwargs: {kwargs}")
            resp2 = MilvusHelper.reset_password(request=request, token=token, **kwargs)
            response.message = resp2.message
            response.root_user = resp2.root_user
            response.success = resp2.success
            response.reset_flag = resp2.reset_flag
            return response
        return ResetPasswordResponse(tenant_code=request.tenant_code, user_name=request.user_name, success=False, message="Password reset failed.", time_taken=0.0), main_logic

    @classmethod
    @service_method(lambda requests, **_: ListResponse(tenant_code=requests.tenant_code, success=True, message="Tenant setup completed successfully.", results={}, time_taken=0.0))
    def set_vector_store(cls, requests: SetVectorStoreRequest, token: str, **kwargs: Any):
        def main_logic(response: ListResponse):
            logger.debug(f"set_vector_store: kwargs received: {kwargs}")
            response.results = MilvusHelper.set_vector_store(tenant_code=requests.tenant_code, token=token, **kwargs)
            return response
        return ListResponse(tenant_code=requests.tenant_code, success=True, message="Tenant setup completed successfully.", results={}, time_taken=0.0), main_logic

    @classmethod
    @service_method(lambda requests, **_: BaseResponse(tenant_code=requests.tenant_code, success=True, message="Vector store inserted successfully.", time_taken=0.0))
    def insert_into_vector_store(cls, requests: InsertEmbeddedRequest, token: str, **kwargs: Any):
        def main_logic(response: BaseResponse):
            logger.debug(f"Insert request: {sanitize_for_log(requests.tenant_code)}")
            num_inserted = MilvusHelper.insert_embedded_data(request=requests, token=token, **kwargs)
            batch_size = len(requests.data)
            flush_status = ("auto-flushed" if batch_size >= 100 or kwargs.get("force_flush") else "deferred")
            response.message = f"Vector store inserted successfully. {num_inserted} vectors inserted ({flush_status})."
            return response
        return BaseResponse(tenant_code=requests.tenant_code, success=True, message="Vector store inserted successfully.", time_taken=0.0), main_logic

    @classmethod
    @service_method(lambda tenant_code, model_name, token, **_: BaseResponse(tenant_code=tenant_code, success=True, message="Collection flushed successfully.", time_taken=0.0))
    def flush_vector_store(cls, tenant_code: str, model_name: str, token: str):
        def main_logic(response: BaseResponse):
            success = MilvusHelper.flush_tenant_collection(tenant_code=tenant_code, model_name=model_name, token=token)
            if not success:
                response.success = False
                response.message = "Failed to flush collection."
            return response
        return BaseResponse(tenant_code=tenant_code, success=True, message="Collection flushed successfully.", time_taken=0.0), main_logic

    @classmethod
    @service_method(lambda requests, token, **_: SearchEmbeddedResponse(
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
    ))
    def search_in_vector_store(cls, requests: SearchEmbeddedRequest, token: str, **kwargs: Any):
        def main_logic(response: SearchEmbeddedResponse):
            logger.debug(f"Search request: {sanitize_for_log(requests.tenant_code)}")
            search_results = MilvusHelper.search_embedded_data(request=requests, token=token, **kwargs)
            response.data = search_results
            if not search_results:
                response.success = False
                response.message = "No vectors found in the vector store."
            return response
        return SearchEmbeddedResponse(
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
        ), main_logic

    @classmethod
    @service_method(lambda request, token, **_: ListResponse(tenant_code=request.tenant_code, success=True, message="Custom schema generated successfully.", results={}, time_taken=0.0))
    def generate_schema(cls, request: GenerateSchemaRequest, token: str, **kwargs: Any):
        def main_logic(response: ListResponse):
            logger.debug(f"Generate schema request: {sanitize_for_log(request.tenant_code)}, model_name: {sanitize_for_log(request.model_name)}")
            response.results = MilvusHelper.generate_schema(
                tenant_code=request.tenant_code,
                model_name=request.model_name,
                dimension=request.dimension,
                nlist=request.nlist,
                metric_type=request.metric_type,
                index_type=request.index_type,
                metadata_length=request.metadata_length,
                drop_ratio_build=request.drop_ratio,
                token=token,
                **kwargs,
            )
            response.message = response.results.get("message", "Custom schema generated successfully.")
            return response
        return ListResponse(tenant_code=request.tenant_code, success=True, message="Custom schema generated successfully.", results={}, time_taken=0.0), main_logic

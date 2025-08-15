# =============================================================================
# File: vector_store_service.py
# Description: Service layer for vector store operations including CRUD and search
# Author: Goutam Malakar
# Date: 2025-01-15
# Version: 1.0.0
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

from time import time
from typing import Any

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


class VectorStoreService:
    """
    Service class for vector store operations.

    Provides high-level business logic for vector store management including
    user management, tenant setup, data insertion, and similarity search.
    All methods are class methods for stateless operation.
    """

    @classmethod
    def set_user(
        cls, request: SetUserRequest, token: str, **kwargs: Any
    ) -> ListResponse:
        """
        Creates or manages a user for the specified tenant.

        Args:
            request (SetUserRequest): Request containing tenant_code and user configuration
            token (str): Authentication token for authorization
            **kwargs: Additional parameters:
                - replace_current_client_id (bool): Whether to replace existing user
                - create_another_client_id (bool): Whether to create additional user

        Returns:
            ListResponse: Response containing user creation details and credentials

        Raises:
            UserManagementError: If user creation or management fails
            MilvusOperationError: If database operations fail
        """
        start_time = time()
        response = ListResponse(
            tenant_code=request.tenant_code,
            success=True,
            message="User set successfully.",
            time_taken=0.0,
            results={},
        )
        try:
            logger.debug(
                f"User set request: {sanitize_for_log(request.tenant_code)}, kwargs: {kwargs}"
            )
            response.results = MilvusHelper.set_user(
                request=request, token=token, **kwargs
            )
            response.message = response.results.get("message", "User set successfully.")
        except UserManagementError as e:
            response.success = False
            response.message = f"User management error: {str(e)}"
            logger.exception("User management error during user set operation")
        except MilvusOperationError as e:
            response.success = False
            response.message = f"Database operation error: {str(e)}"
            logger.exception("Database error during user set operation")
        except Exception as e:
            response.success = False
            response.message = f"Unexpected error setting user: {str(e)}"
            logger.exception("Unexpected error during user set operation")
        finally:
            response.time_taken = time() - start_time
            logger.debug(
                f"User set operation completed in {response.time_taken:.2f} seconds."
            )
            return response

    @classmethod
    def reset_password(
        cls, request: ResetPasswordRequest, token: str, **kwargs: Any
    ) -> ResetPasswordResponse:
        """
        Resets a user's password with policy validation.

        Args:
            request (ResetPasswordRequest): Request containing:
                - tenant_code (str): Tenant identifier
                - user_name (str): Username to reset password for
                - old_password (str): Current password for verification
                - new_password (str): New password meeting policy requirements
            token (str): Authentication token for authorization
            **kwargs: Additional parameters for password reset operation

        Returns:
            ResetPasswordResponse: Response containing:
                - success (bool): Whether password reset succeeded
                - root_user (bool): Whether user is admin/root user
                - reset_flag (bool): Whether password was actually reset
                - message (str): Operation result message

        Raises:
            UserManagementError: If password reset fails
            MilvusOperationError: If database operations fail
        """
        start_time = time()
        response = ResetPasswordResponse(
            tenant_code=request.tenant_code,
            user_name=request.user_name,
            success=False,
            message="Password reset failed.",
            time_taken=0.0,
        )
        try:
            logger.debug(
                f"Password reset request: {sanitize_for_log(request.tenant_code)}, kwargs: {kwargs}"
            )
            resp2 = MilvusHelper.reset_password(request=request, token=token, **kwargs)
            response.message = resp2.message
            response.root_user = resp2.root_user
            response.success = resp2.success
            response.reset_flag = resp2.reset_flag
        except UserManagementError as e:
            response.success = False
            response.message = f"Password reset error: {str(e)}"
            logger.exception("User management error during password reset operation")
        except MilvusOperationError as e:
            response.success = False
            response.message = f"Database operation error: {str(e)}"
            logger.exception("Database error during password reset operation")
        except Exception as e:
            response.success = False
            response.message = f"Unexpected error resetting password: {str(e)}"
            logger.exception("Unexpected error during password reset operation")
        finally:
            response.time_taken = time() - start_time
            logger.debug(
                f"Password reset operation completed in {response.time_taken:.2f} seconds."
            )
            return response

    @classmethod
    def set_vector_store(
        cls, requests: SetVectorStoreRequest, token: str, **kwargs: Any
    ) -> ListResponse:
        """
        Sets up database, user, and permissions for the given tenant.
        Does NOT create collections or indexes.

        Args:
            requests (SetVectorStoreRequest): The request object with tenant, token, and vector dimension.
            **kwargs: Any extra keyword arguments to pass to MilvusHelper.set_vector_store.

        Returns:
            ListResponse: The response with tenant setup details.
        """
        start_time = time()
        response = ListResponse(
            tenant_code=requests.tenant_code,
            success=True,
            message="Tenant setup completed successfully.",
            results={},
            time_taken=0.0,
        )
        try:
            logger.debug(f"set_vector_store: kwargs received: {kwargs}")
            response.results = MilvusHelper.set_vector_store(
                tenant_code=requests.tenant_code,
                token=token,
                **kwargs,
            )
        except VectorStoreError as e:
            response.success = False
            response.message = f"Tenant setup error: {str(e)}"
            logger.exception("Vector store error during tenant setup")
        except MilvusOperationError as e:
            response.success = False
            response.message = f"Database operation error: {str(e)}"
            logger.exception("Database error during tenant setup")
        except Exception as e:
            response.success = False
            response.message = f"Unexpected error during tenant setup: {str(e)}"
            logger.exception("Unexpected error during tenant setup")
        finally:
            response.time_taken = time() - start_time
            logger.debug(
                f"Tenant setup operation completed in {response.time_taken:.2f} seconds."
            )
            return response

    @classmethod
    def insert_into_vector_store(
        cls, requests: InsertEmbeddedRequest, token: str, **kwargs: Any
    ) -> BaseResponse:
        """
        Inserts embedded vectors into the vector store for the given tenant.

        Args:
            requests (InsertEmbeddedRequest): The request object with tenant, token, and data.
            **kwargs: Any extra keyword arguments to pass to MilvusHelper.insert_embedded_data.

        Returns:
            BaseResponse: The response with insertion details.
        """
        start_time = time()
        response = BaseResponse(
            tenant_code=requests.tenant_code,
            success=True,
            message="Vector store inserted successfully.",
            time_taken=0.0,
        )
        try:
            logger.debug(f"Insert request: {sanitize_for_log(requests.tenant_code)}")
            num_inserted = MilvusHelper.insert_embedded_data(
                request=requests,
                token=token,
                **kwargs,
            )
            batch_size = len(requests.data)
            flush_status = (
                "auto-flushed"
                if batch_size >= 100 or kwargs.get("force_flush")
                else "deferred"
            )
            response.message = f"Vector store inserted successfully. {num_inserted} vectors inserted ({flush_status})."
        except ValidationError as ve:
            response.success = False
            response.message = f"Validation error: {str(ve)}"
            logger.exception("Validation error during vector store insert operation")
        except ValueError as ve:
            response.success = False
            response.message = f"Invalid data: {str(ve)}"
            logger.exception(
                "Data validation error during vector store insert operation"
            )
        except VectorStoreError as e:
            response.success = False
            response.message = f"Vector store error: {str(e)}"
            logger.exception("Vector store error during insert operation")
        except MilvusOperationError as e:
            response.success = False
            response.message = f"Database operation error: {str(e)}"
            logger.exception("Database error during vector store insert operation")
        except Exception as e:
            response.success = False
            response.message = f"Unexpected error inserting vector store: {str(e)}"
            logger.exception("Unexpected error during vector store insert operation")
        finally:
            response.time_taken = time() - start_time
            logger.debug(
                f"Insert operation completed in {response.time_taken:.2f} seconds (batch: {len(requests.data)})."
            )
            return response

    @classmethod
    def flush_vector_store(
        cls, tenant_code: str, model_name: str, token: str
    ) -> BaseResponse:
        """
        Manually flush a tenant's vector store collection to ensure data persistence.

        Args:
            tenant_code (str): Tenant identifier
            model_name (str): Model name for collection identification
            token (str): Authentication token for authorization

        Returns:
            BaseResponse: Response indicating flush operation success/failure

        Raises:
            VectorStoreError: If flush operation fails
        """
        start_time = time()
        response = BaseResponse(
            tenant_code=tenant_code,
            success=True,
            message="Collection flushed successfully.",
            time_taken=0.0,
        )
        try:
            success = MilvusHelper.flush_tenant_collection(
                tenant_code=tenant_code, model_name=model_name, token=token
            )
            if not success:
                response.success = False
                response.message = "Failed to flush collection."
        except Exception as e:
            response.success = False
            response.message = f"Error flushing collection: {str(e)}"
        finally:
            response.time_taken = time() - start_time
            return response

    @classmethod
    def search_in_vector_store(
        cls, requests: SearchEmbeddedRequest, token: str, **kwargs: Any
    ) -> SearchEmbeddedResponse:
        """
        Searches for embedded vectors in the vector store for the given tenant.

        Args:
            requests (SearchEmbeddedRequest): The request object with tenant, token, and search parameters.
            **kwargs: Any extra keyword arguments to pass to MilvusHelper.search_embedded_data.

        Returns:
            BaseResponse: The response with search details.
        """
        start_time = time()
        response = SearchEmbeddedResponse(
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
        )
        try:
            logger.debug(f"Search request: {sanitize_for_log(requests.tenant_code)}")
            search_results = MilvusHelper.search_embedded_data(
                request=requests,
                token=token,
                **kwargs,
            )
            response.data = search_results
            if not search_results:
                response.success = False
                response.message = "No vectors found in the vector store."
        except SearchError as e:
            response.success = False
            response.message = f"Search error: {str(e)}"
            logger.exception("Search error during vector store search operation")
        except VectorStoreError as e:
            response.success = False
            response.message = f"Vector store error: {str(e)}"
            logger.exception("Vector store error during search operation")
        except MilvusOperationError as e:
            response.success = False
            response.message = f"Database operation error: {str(e)}"
            logger.exception("Database error during vector store search operation")
        except Exception as e:
            response.success = False
            response.message = f"Unexpected error searching vector store: {str(e)}"
            logger.exception("Unexpected error during vector store search operation")
        finally:
            response.time_taken = time() - start_time
            logger.debug(
                f"Search operation completed in {response.time_taken:.2f} seconds."
            )
            return response

    @classmethod
    def generate_schema(
        cls, request: GenerateSchemaRequest, token: str, **kwargs: Any
    ) -> ListResponse:
        """
        Generates a custom schema for the given tenant with specified parameters.

        Args:
            request (GenerateSchemaRequest): The request object with tenant, model, and schema parameters.
            token (str): The token for authentication.
            **kwargs: Any extra keyword arguments to pass to MilvusHelper.generate_schema.

        Returns:
            ListResponse: The response with schema generation details.
        """
        start_time = time()
        response = ListResponse(
            tenant_code=request.tenant_code,
            success=True,
            message="Custom schema generated successfully.",
            results={},
            time_taken=0.0,
        )
        try:
            logger.debug(
                f"Generate schema request: {sanitize_for_log(request.tenant_code)}, model: {sanitize_for_log(request.model_name)}"
            )
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
            response.message = response.results.get(
                "message", "Custom schema generated successfully."
            )
        except VectorStoreError as e:
            response.success = False
            response.message = f"Schema generation error: {str(e)}"
            logger.exception("Vector store error during schema generation")
        except MilvusOperationError as e:
            response.success = False
            response.message = f"Database operation error: {str(e)}"
            logger.exception("Database error during schema generation")
        except ValidationError as e:
            response.success = False
            response.message = f"Validation error: {str(e)}"
            logger.exception("Validation error during schema generation")
        except Exception as e:
            response.success = False
            response.message = f"Unexpected error generating schema: {str(e)}"
            logger.exception("Unexpected error during schema generation")
        finally:
            response.time_taken = time() - start_time
            logger.debug(
                f"Schema generation operation completed in {response.time_taken:.2f} seconds."
            )
            return response

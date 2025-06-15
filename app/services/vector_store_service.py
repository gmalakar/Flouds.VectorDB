# =============================================================================
# File: base_nlp_service.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import time
from typing import Any

from app.logger import get_logger
from app.milvus.milvus_helper import MilvusHelper
from app.models.base_request import BaseRequest
from app.models.base_response import BaseResponse
from app.models.insert_request import InsertEmbeddedRequest
from app.models.list_response import ListResponse
from app.models.search_request import SearchEmbeddedRequest
from app.models.search_response import SearchEmbeddedResponse
from app.models.set_vector_store_request import SetVectorStoreRequest

logger = get_logger("vector_store_service")


class VectorStoreService:
    """
    Service class for vector store operations.
    """

    @classmethod
    def set_user(cls, request: BaseRequest, token: str, **kwargs: Any) -> ListResponse:
        """
        Sets a user in the vector store for the given tenant.

        Args:
            request (BaseRequest): The request object containing tenant and token info.
            token (str): The token for authentication.
            **kwargs: Any extra keyword arguments to pass to MilvusHelper.set_user.

        Returns:
            ListResponse: The response with operation details.
        """
        start_time: float = time.time()
        response: ListResponse = ListResponse(
            for_tenant=request.tenant_code,
            success=True,
            message="User set successfully.",
            time_taken=0.0,
            results={},
        )
        try:
            logger.debug(f"User set request: {request.tenant_code}, kwargs: {kwargs}")
            response.results = MilvusHelper.set_user(
                tenant_code=request.tenant_code, token=token, **kwargs
            )
            response.message = response.results.get("message", "User set successfully.")
        except Exception as e:
            response.success = False
            response.message = f"Error setting user: {str(e)}"
            logger.exception("Unexpected error during user set operation")
        finally:
            elapsed: float = time.time() - start_time
            logger.debug(f"User set operation completed in {elapsed:.2f} seconds.")
            response.time_taken = elapsed
            return response

    @classmethod
    def set_vector_store(
        cls, requests: SetVectorStoreRequest, token: str, **kwargs: Any
    ) -> ListResponse:
        """
        Sets or retrieves a vector store for the given tenant.

        Args:
            requests (SetVectorStoreRequest): The request object with tenant, token, and vector dimension.
            **kwargs: Any extra keyword arguments to pass to MilvusHelper.set_vector_store.

        Returns:
            ListResponse: The response with vector store details.
        """
        start_time: float = time.time()
        response: ListResponse = ListResponse(
            for_tenant=requests.tenant_code,
            success=True,
            message="vector store set or retrieved successfully.",
            results={},
            time_taken=0.0,
        )
        try:
            logger.debug(f"vector store request: {requests.tenant_code}")
            response.results = MilvusHelper.set_vector_store(
                tenant_code=requests.tenant_code,
                token=token,
                vector_dimension=requests.vector_dimension,
                **kwargs,
            )
        except Exception as e:
            response.success = False
            response.message = f"Error generating vector store: {str(e)}"
            logger.exception("Unexpected error during vector store operation")
        finally:
            elapsed: float = time.time() - start_time
            logger.debug(f"Vector store operation completed in {elapsed:.2f} seconds.")
            response.time_taken = elapsed
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
        start_time: float = time.time()
        response: BaseResponse = BaseResponse(
            for_tenant=requests.tenant_code,
            success=True,
            message="Vector store inserted successfully.",
            time_taken=0.0,
        )
        try:
            logger.debug(f"vector store request: {requests.tenant_code}")
            num_inserted: int = MilvusHelper.insert_embedded_data(
                request=requests,
                token=token,
                **kwargs,
            )
            response.message = (
                f"Vector store inserted successfully. {num_inserted} vectors inserted."
            )
        except Exception as e:
            response.success = False
            response.message = f"Error in inserting vector store: {str(e)}"
            logger.exception("expected error during vector store operation")
        finally:
            elapsed: float = time.time() - start_time
            logger.debug(f"insert operation completed in {elapsed:.2f} seconds.")
            response.time_taken = elapsed
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
        start_time: float = time.time()
        response: SearchEmbeddedResponse = SearchEmbeddedResponse(
            for_tenant=requests.tenant_code,
            model=requests.model,
            limit=requests.limit,
            offset=requests.offset,
            nprobe=requests.nprobe,
            round_decimal=requests.round_decimal,
            score_threshold=requests.score_threshold,
            metric_type=requests.metric_type,
            success=True,
            message="Vector store search completed successfully.",
            time_taken=0.0,
            data=[],  # <-- Add this line!
        )
        try:
            logger.debug(f"vector store request: {requests.tenant_code}")
            search_results = MilvusHelper.search_embedded_data(
                request=requests,
                token=token,
                **kwargs,
            )
            response.data = search_results
            if not search_results:
                response.success = False
                response.message = "No vectors found in the vector store."
            else:
                response.success = True
        except Exception as e:
            response.success = False
            response.message = f"Error in searching vector store: {str(e)}"
            logger.exception("expected error during vector store operation")
        finally:
            elapsed: float = time.time() - start_time
            logger.debug(f"search operation completed in {elapsed:.2f} seconds.")
            response.time_taken = elapsed
            return response

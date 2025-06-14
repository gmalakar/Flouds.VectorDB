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
from app.models.database_info import DatabaseInfoResponse
from app.models.insert_request import InsertEmbeddedRequest
from app.models.list_responses import ListResponse
from app.models.set_vector_store_request import SetVectorStoreRequest

logger = get_logger("vector_store_service")


class VectorStoreService:

    @classmethod
    def set_user(cls, request: BaseRequest, **kwargs: Any) -> ListResponse:
        start_time = time.time()
        response = ListResponse(
            for_tenant=request.for_tenant,
            success=True,
            message="User set successfully.",
            time_taken=0.0,
        )
        try:
            logger.debug(f"User set request: {request.for_tenant}")
            response.results = MilvusHelper.set_user(
                tenant_code=request.for_tenant, **kwargs
            )
            response.message = response.results["message"]
        except Exception as e:
            response.success = False
            response.message = f"Error setting user: {str(e)}"
            logger.exception("Unexpected error during user set operation")
        finally:
            elapsed = time.time() - start_time
            logger.debug(f"User set operation completed in {elapsed:.2f} seconds.")
            response.time_taken = elapsed
            return response

    @classmethod
    def set_vector_store(
        cls, requests: SetVectorStoreRequest, **kwargs: Any
    ) -> DatabaseInfoResponse:
        start_time = time.time()
        response = DatabaseInfoResponse(
            for_tenant=requests.for_tenant,
            success=True,
            message="vector store set or retrieved successfully.",
            results={},
            time_taken=0.0,
        )
        try:
            logger.debug(f"vector store request: {requests.for_tenant}")
            response.results = MilvusHelper.set_vector_store(
                tenant_code=requests.for_tenant,
                token=requests.token,
                vector_dimension=requests.vector_dimension,
                **kwargs,
            )
        except Exception as e:
            response.success = False
            response.message = f"Error generating vector store: {str(e)}"
            logger.exception("Unexpected error during vector store operation")
        finally:
            elapsed = time.time() - start_time
            logger.debug(f"Vector store operation completed in {elapsed:.2f} seconds.")
            response.time_taken = elapsed
            return response

    @classmethod
    def insert_into_vector_store(
        cls, requests: InsertEmbeddedRequest, **kwargs: Any
    ) -> BaseResponse:
        start_time = time.time()
        response = BaseResponse(
            for_tenant=requests.for_tenant,
            success=True,
            message="Vector store inserted successfully.",
            time_taken=0.0,
        )
        try:
            logger.debug(f"vector store request: {requests.for_tenant}")
            num_inserted = MilvusHelper.insert_embedded_data(
                embedded_vector=requests.data,
                tenant_code=requests.for_tenant,
                token=requests.token,
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
            elapsed = time.time() - start_time
            logger.debug(f"insert operation completed in {elapsed:.2f} seconds.")
            response.time_taken = elapsed
            return response

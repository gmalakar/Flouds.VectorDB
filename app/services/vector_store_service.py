# =============================================================================
# File: base_nlp_service.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import asyncio
import threading
import time
from typing import Any

from pymilvus import connections

from app.config.config_loader import ConfigLoader
from app.helpers.milvus_helper import MilvusHelper
from app.logger import get_logger
from app.models.database_info import DatabaseInfoResponse
from app.models.milvus_db_info import MilvusDBInfo
from app.models.set_vector_store_request import SetVectorStoreRequest
from app.modules.concurrent_dict import ConcurrentDict

logger = get_logger("vector_store_service")


class VectorStoreService:
    @classmethod
    def set_vector_store(
        cls, requests: SetVectorStoreRequest, **kwargs: Any
    ) -> DatabaseInfoResponse:
        start_time = time.time()
        response = DatabaseInfoResponse(
            for_tenant=requests.for_tenant,
            success=True,
            message="vector store set or retrieved successfully.",
            results=MilvusDBInfo(
                tenant_db=requests.for_tenant,
                client_id=requests.client_id,
                secret_key=requests.client_secret,
            ),
            time_taken=0.0,
        )
        try:
            logger.debug(f"vector store request: {requests.for_tenant}")
            response.results = MilvusHelper.set_vector_store(
                tenant_code=requests.for_tenant,
                vector_dimension=requests.vector_dimension,
                client_id=requests.client_id,
                secret_key=requests.client_secret,
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

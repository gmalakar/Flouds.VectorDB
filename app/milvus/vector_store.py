# =============================================================================
# File: vector_store.py
# Date: 2025-06-14
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import json
from threading import Lock
from typing import Any, List, Optional

from pymilvus import Collection, MilvusClient  # Adjust if needed

from app.app_init import APP_SETTINGS
from app.logger import get_logger
from app.milvus.base_milvus import BaseMilvus
from app.models.embeded_meta import EmbeddedMeta
from app.models.embeded_vector import EmbeddedVector
from app.models.search_request import SearchEmbeddedRequest

logger = get_logger("Vector Store")


class VectorStore(BaseMilvus):
    _milvus_admin_client: Optional[MilvusClient] = None
    # _db_name: Optional[str] = None
    # _store_name: Optional[str] = None

    def __init__(
        self, tenant_code: str, user_id: str, password: str, dimension: int = 0
    ):
        logger.debug(
            f"Initializing VectorStore for tenant '{tenant_code}' with user '{user_id}'"
        )
        super().__init__()
        if not tenant_code or not user_id or not password:
            logger.error(
                "Tenant code, user ID, and password must be provided to initialize VectorStore."
            )
            raise ValueError(
                "Tenant code, user ID, and password must be provided to initialize VectorStore."
            )
        logger.debug(
            f"Initializing super for tenant '{tenant_code}' with user '{user_id}'"
        )

        self._tenant_code: str = tenant_code
        self._user_id: str = user_id
        self._password: str = password
        self._tenant_role_name: str = BaseMilvus._get_tenant_role_name_by_tenant_code(
            tenant_code
        )
        self._vector_dimension: int = dimension
        if dimension <= 0:
            self._vector_dimension = APP_SETTINGS.vectordb.default_dimension
        logger.debug(
            f"Using default vector dimension: {self._vector_dimension} for tenant '{tenant_code}'"
        )
        self._db_name: str = BaseMilvus._get_db_name_by_tenant_code(tenant_code)
        self._store_name: str = BaseMilvus._get_vector_store_name_by_tenant_code(
            self._tenant_code
        )
        self._tenant_client: Optional[MilvusClient] = None
        self._has_collection: Optional[Collection] = False
        self._has_index: Optional[str] = False
        self._lock: Lock = Lock()

    def _get_tenant_client(self) -> MilvusClient:
        if self._tenant_client is None:
            # HINT: Ensure APP_SETTINGS is loaded before this call
            self._tenant_client = BaseMilvus._get_tenant_client(
                tenant_client_id=self._user_id,
                tenant_client_secret=self._password,
                tenant_database=self._db_name,
            )
        return self._get_or_create_tenant_connection(self._tenant_code)

    @staticmethod
    def __convert_to_field_data(response: List[EmbeddedVector]) -> List[dict]:
        # Return a list of dicts matching the schema (excluding auto_id "id")
        return [
            {
                "chunk": e.chunk,
                "model": e.model.lower(),
                "vector": e.vector,
                "meta": (
                    json.dumps(e.metadata) if e.metadata else "{}"
                ),  # Add meta as JSON string
            }
            for e in response
        ]

    def insert_data(self, vector: List[EmbeddedVector], **kwargs: Any) -> None:
        """
        Inserts embedded vectors into the Milvus collection for this tenant.

        Args:
            vector (List[EmbeddedVectors]): The vectors to insert.
            **kwargs: Extra metadata to store as JSON in the 'meta' field.

        Raises:
            Exception: If insertion fails.
        """
        try:
            for i, e in enumerate(vector):
                logger.debug(f"Item {i}: vector length = {len(e.vector)}")
            logger.info(
                f"Inserting {len(vector)} vectors into Milvus collection '{self._store_name}'"
            )
            if not self.__set_collection():
                raise Exception(f"Failed to set collection for {self._store_name}")
            logger.debug(
                f"Setting collection for tenant '{self._tenant_code}' with user '{self._user_id}'"
            )
            client = self._get_tenant_client()
            logger.debug(f"Using tenant client for collection '{self._store_name}'")
            client.insert(
                collection_name=self._store_name,
                data=self.__convert_to_field_data(vector),
                partition_name=kwargs.get("partition_name", ""),
            )
            logger.info(
                f"Successfully inserted {len(vector)} vectors into Milvus collection '{self._store_name}'"
            )
            client.flush(self._store_name)
        except Exception as ex:
            logger.exception(f"Error inserting data into Milvus collection: {ex}")
            raise Exception("Error inserting data into Milvus collection") from ex

    # def search_embedded_data(
    #     self, text_to_search: str, vector: List[float], parameters: dict
    # ) -> dict:
    #     try:
    #         results = self.search_store(vector, parameters)
    #         if results:
    #             return {
    #                 "status": "OK",
    #                 "results": results,
    #                 "message": f"Found matching chunk for text '{text_to_search}'",
    #             }
    #         else:
    #             return {
    #                 "status": "no chunks found",
    #                 "message": f"Could not find any matching chunk for text '{text_to_search}'",
    #             }
    #     except Exception as ex:
    #         logger.error(f"Exception during search: {ex}")
    #         return {"status": "Exception", "message": str(ex)}

    def search_store(
        self, request: SearchEmbeddedRequest, **kwargs
    ) -> List[EmbeddedMeta]:
        if self.__set_collection() is False:
            raise Exception(f"Failed to set collection for {self._store_name}")
        results: List[EmbeddedMeta] = []
        client = self._get_tenant_client()

        model = request.model.lower()
        expr = f'model == "{model}"' if model else ""

        params = {}
        for key in ["nprobe", "ef", "radius", "range_filter"]:
            value = kwargs.get(key, getattr(request, key, None))
            if value is not None:
                params[key] = value

        search_params = {
            "metric_type": kwargs.get(
                "metric_type", getattr(request, "metric_type", None)
            ),
            "params": params,
            "output_fields": BaseMilvus.get_chunk_meta_output_fields(),
        }
        # Only add optional top-level keys if not None
        for key in [
            "limit",
            "offset",
            "expr",
            "partition_names",
            "score_threshold",
            "timeout",
            "round_decimal",
            "_async",
            "_callback",
            "consistency_level",
            "guarantee_timestamp",
            "graceful_time",
            "travel_timestamp",
        ]:
            value = kwargs.get(key, getattr(request, key, None))
            if value is not None:
                search_params[key] = value

        result = client.search(
            collection_name=self._store_name,
            data=[request.vector],
            anns_field="vector",
            search_params=search_params,
            limit=search_params.get("limit"),
            output_fields=search_params["output_fields"],
        )

        # Parse results as needed
        for hits in result:
            for hit in hits:
                chunk = hit.entity.get("chunk")
                if chunk:
                    meta = hit.entity.get("meta", "{}")
                    if isinstance(meta, str):
                        meta = json.loads(meta)
                    embeded_meta = EmbeddedMeta(
                        content=chunk,
                        meta=meta,
                    )
                    results.append(embeded_meta)
        logger.debug(
            f"Retrieved {len(results)} results from vector store '{self._store_name}'"
        )
        return results

    def __set_collection(self) -> bool:
        """
        Gets the collection for this tenant, creating it (and its index/privileges) if it does not exist.
        Handles and logs errors if collection creation fails.
        Uses a lock to ensure thread safety during collection creation.
        """
        try:

            client = self._get_tenant_client()
            if client.has_collection(self._store_name):
                logger.info(f"Vector store '{self._store_name}' already exists.")
                # Always ensure index exists before loading
                if not self._has_index:
                    BaseMilvus._create_vector_store_index_if_not_exists(
                        self._store_name, self._tenant_code
                    )
                client.load_collection(self._store_name)
                logger.info(f"Vector store '{self._store_name}' loaded.")
                self._has_collection = True
            else:
                logger.info(
                    f"Vector store '{self._store_name}' does not exist. so create it."
                )
                BaseMilvus._setup_tenant_vector_store(
                    tenant_code=self._tenant_code,
                    user_id=self._user_id,
                    vector_dimension=self._vector_dimension,
                )
            return True
        except Exception as ex:
            logger.error(f"Error in _set_collection for '{self._store_name}': {ex}")
            raise Exception(f"Error in _set_collection for '{self._store_name}': {ex}")

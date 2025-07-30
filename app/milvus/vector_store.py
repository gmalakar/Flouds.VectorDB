# =============================================================================
# File: vector_store.py
# Date: 2025-06-14
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import json
from threading import Lock
from typing import Any, List, Optional

from pymilvus import Collection, MilvusClient

from app.app_init import APP_SETTINGS
from app.logger import get_logger
from app.milvus.base_milvus import BaseMilvus
from app.models.embedded_meta import EmbeddedMeta
from app.models.embedded_vector import EmbeddedVector
from app.models.search_request import SearchEmbeddedRequest

logger = get_logger("Vector Store")


class VectorStore(BaseMilvus):
    """
    Thread-safe wrapper for Milvus vector store operations for a tenant.
    Handles collection creation, upsert, and search.
    """

    _milvus_admin_client: Optional[MilvusClient] = None

    OPTIONAL_SEARCH_KEYS = [
        "partition_names",
        "timeout",
        "_async",
        "_callback",
        "consistency_level",
        "guarantee_timestamp",
        "graceful_time",
        "travel_timestamp",
    ]

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

        self._tenant_code: str = tenant_code
        self._user_id: str = user_id
        self._password: str = password
        self._tenant_role_name: str = BaseMilvus._get_tenant_role_name_by_tenant_code(
            tenant_code
        )
        self._vector_dimension: int = (
            dimension
            if dimension > 0
            else getattr(APP_SETTINGS.vectordb, "default_dimension", 768)
        )
        logger.debug(
            f"Using vector dimension: {self._vector_dimension} for tenant '{tenant_code}'"
        )
        self._db_name: str = BaseMilvus._get_db_name_by_tenant_code(tenant_code)
        self._store_name: str = BaseMilvus._get_vector_store_name_by_tenant_code(
            self._tenant_code
        )
        self._tenant_client: Optional[MilvusClient] = None
        self._has_collection: bool = False
        self._has_index: bool = False
        self._lock: Lock = Lock()

    def _get_tenant_client(self) -> MilvusClient:
        """
        Returns a MilvusClient for this tenant, creating it if needed.
        """
        if self._tenant_client is None:
            self._tenant_client = BaseMilvus._get_tenant_client(
                tenant_client_id=self._user_id,
                tenant_client_secret=self._password,
                tenant_database=self._db_name,
            )
        return self._get_or_create_tenant_connection(self._tenant_code)

    @staticmethod
    def __convert_to_field_data(response: List[EmbeddedVector]) -> List[dict]:
        """
        Converts a list of EmbeddedVector objects to Milvus upsert-ready dicts.
        """
        vector_field_name = BaseMilvus._get_vector_field_name()
        primary_key_name = BaseMilvus._get_primary_key_name()
        return [
            {
                primary_key_name: e.key,
                "chunk": e.chunk,
                "model": e.model.lower(),
                vector_field_name: e.vector,
                "meta": json.dumps(e.metadata) if e.metadata else "{}",
            }
            for e in response
        ]

    def insert_data(self, vector: List[EmbeddedVector], **kwargs: Any) -> None:
        """
        Upserts embedded vectors into the Milvus collection for this tenant.
        Thread-safe.
        """
        with self._lock:
            try:
                primary_key_name = BaseMilvus._get_primary_key_name()
                logger.debug(f"Primary key name for upsert: {primary_key_name}")

                logger.info(
                    f"Upserting {len(vector)} vectors into Milvus collection '{self._store_name}'"
                )
                if not self.__set_collection():
                    raise Exception(f"Failed to set collection for {self._store_name}")
                logger.debug(
                    f"Setting collection for tenant '{self._tenant_code}' with user '{self._user_id}'"
                )
                client = self._get_tenant_client()
                logger.debug(f"Using tenant client for collection '{self._store_name}'")

                data_to_upsert = self.__convert_to_field_data(vector)

                client.upsert(
                    collection_name=self._store_name,
                    data=data_to_upsert,
                    partition_name=kwargs.get("partition_name", ""),
                )

                logger.info(
                    f"Successfully upserted {len(vector)} vectors into Milvus collection '{self._store_name}'"
                )
                client.flush(self._store_name)
            except Exception as ex:
                logger.exception(f"Error upserting data into Milvus collection: {ex}")
                raise Exception("Error upserting data into Milvus collection") from ex

    def search_store(
        self, request: SearchEmbeddedRequest, **kwargs
    ) -> List[EmbeddedMeta]:
        """
        Searches for embedded data in the tenant's vector store.
        Returns a list of EmbeddedMeta results.
        Thread-safe.
        """
        if not self.__set_collection():
            raise Exception(f"Failed to set collection for {self._store_name}")
        results: List[EmbeddedMeta] = []
        client = self._get_tenant_client()

        vector_field_name = BaseMilvus._get_vector_field_name()
        model = request.model.lower().strip() if request.model else ""
        filter_expr = f'model == "{model}"' if model else None

        search_params = {
            "search_params": {
                "metric_type": request.metric_type or "COSINE",
                "params": {"nprobe": min(request.nprobe or 10, 32)},
            },
            "limit": min(request.limit or 10, 100),
            "offset": request.offset or 0,
            "round_decimal": request.round_decimal or 4,
            "output_fields": ["chunk", "meta"],
            "consistency_level": "Eventually",
        }

        if filter_expr:
            search_params["filter"] = filter_expr

        for key in ["radius", "range_filter"]:
            if key in kwargs:
                search_params["search_params"]["params"][key] = kwargs[key]

        for key in self.OPTIONAL_SEARCH_KEYS:
            if key in kwargs:
                search_params[key] = kwargs[key]

        result = client.search(
            collection_name=self._store_name,
            data=[request.vector],
            anns_field=vector_field_name,
            **search_params,
        )

        # Fast result processing
        filtered_results = []
        score_threshold = getattr(request, "score_threshold", None)
        
        if result and len(result) > 0:
            hits = result[0]
            for hit in hits:
                if score_threshold is not None and hit.score < score_threshold:
                    continue
                
                chunk = hit.entity.get("chunk")
                if not chunk:
                    continue
                    
                meta = hit.entity.get("meta", "{}")
                if request.meta_required:
                    parsed_meta = self._parse_meta(meta)
                    if not parsed_meta or parsed_meta == {}:
                        continue
                    meta = parsed_meta
                else:
                    meta = self._parse_meta(meta) if isinstance(meta, str) else meta
                
                filtered_results.append(EmbeddedMeta(content=chunk, meta=meta))

        logger.debug(
            f"Retrieved {len(filtered_results)} results from vector store '{self._store_name}'"
        )
        return filtered_results

    @staticmethod
    def _parse_meta(meta):
        """
        Robustly parse meta field from string or dict.
        """
        if isinstance(meta, str):
            try:
                return json.loads(meta)
            except json.JSONDecodeError:
                return {}
        return meta if isinstance(meta, dict) else {}

    def __set_collection(self) -> bool:
        """
        Ensures the collection for this tenant exists and is loaded.
        Creates the collection and index if missing.
        Thread-safe.
        """
        with self._lock:
            try:
                client = self._get_tenant_client()
                if client.has_collection(self._store_name):
                    logger.info(f"Vector store '{self._store_name}' already exists.")
                    if not self._has_index:
                        BaseMilvus._create_vector_store_index_if_not_exists(
                            self._store_name, self._tenant_code
                        )
                        self._has_index = True
                    client.load_collection(self._store_name)
                    logger.info(f"Vector store '{self._store_name}' loaded.")
                    self._has_collection = True
                else:
                    logger.info(
                        f"Vector store '{self._store_name}' does not exist. Creating it."
                    )
                    BaseMilvus._setup_tenant_vector_store(
                        tenant_code=self._tenant_code,
                        user_id=self._user_id,
                        vector_dimension=self._vector_dimension,
                    )
                    self._has_collection = True
                    self._has_index = True
                return True
            except Exception as ex:
                logger.error(f"Error in _set_collection for '{self._store_name}': {ex}")
                raise

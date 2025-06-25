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

    # Static array of optional keys
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
        # Use the dynamic vector field name from BaseMilvus
        vector_field_name = BaseMilvus._get_vector_field_name()
        primary_key_name = BaseMilvus._get_primary_key_name()
        return [
            {
                primary_key_name: e.key,  # Use dynamic primary key name
                "chunk": e.chunk,
                "model": e.model.lower(),
                vector_field_name: e.vector,  # Use dynamic field name
                "meta": (
                    json.dumps(e.metadata) if e.metadata else "{}"
                ),  # Add meta as JSON string
            }
            for e in response
        ]

    def insert_data(self, vector: List[EmbeddedVector], **kwargs: Any) -> None:
        """
        Upserts embedded vectors into the Milvus collection for this tenant.
        The primary key for each vector is taken from the 'key' field of each EmbeddedVector.
        The primary key name is determined by BaseMilvus._get_primary_key_name().

        Args:
            vector (List[EmbeddedVector]): The vectors to insert/upsert.
            **kwargs: Extra metadata to store as JSON in the 'meta' field.

        Raises:
            Exception: If upsert fails.
        """
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

            # Prepare data for upsert: use each vector's key as the primary key
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
        if self.__set_collection() is False:
            raise Exception(f"Failed to set collection for {self._store_name}")
        results: List[EmbeddedMeta] = []
        client = self._get_tenant_client()

        vector_field_name = BaseMilvus._get_vector_field_name()
        model = request.model.lower().strip() if request.model else ""
        filter_expr = f'model == "{model}"' if model else None

        kwargs2 = {
            "search_params": {
                "metric_type": request.metric_type or "COSINE",
                "params": {"nprobe": request.nprobe or 16},
            },
            "limit": request.limit or 10,
            "offset": request.offset or 0,
            "round_decimal": request.round_decimal or 6,
            "output_fields": BaseMilvus.get_chunk_meta_output_fields(),
        }

        if filter_expr:
            kwargs2["filter"] = filter_expr

        for key in ["radius", "range_filter"]:
            if key in kwargs:
                kwargs2["search_params"]["params"][key] = kwargs[key]

        for key in self.OPTIONAL_SEARCH_KEYS:
            if key in kwargs:
                kwargs2[key] = kwargs[key]

        result = client.search(
            collection_name=self._store_name,
            data=[request.vector],
            anns_field=vector_field_name,
            **kwargs2,
        )

        filtered_results = []
        score_threshold = getattr(request, "score_threshold", None)
        for hits in result:
            for hit in hits:
                if score_threshold is not None and hit.score < score_threshold:
                    continue
                chunk = hit.entity.get("chunk")
                if chunk:
                    meta = hit.entity.get("meta", "{}")
                    try:
                        if isinstance(meta, str):
                            meta = json.loads(meta)
                    except json.JSONDecodeError:
                        meta = {}
                    if request.meta_required and (not meta or meta == {}):
                        continue
                    embedded_meta = EmbeddedMeta(
                        content=chunk,
                        meta=meta,
                    )
                    filtered_results.append(embedded_meta)

        logger.debug(
            f"Retrieved {len(filtered_results)} results from vector store '{self._store_name}'"
        )
        return filtered_results

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
                    self._has_index = True
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

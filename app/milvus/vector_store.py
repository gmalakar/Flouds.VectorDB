import json
from threading import Lock
from typing import Any, List, Optional

from pymilvus import Collection, MilvusClient  # Adjust if needed

from app.app_init import APP_SETTINGS
from app.logger import get_logger
from app.milvus.base_milvus import BaseMilvus
from app.models.embeded_vectors import EmbeddedVectors

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
    def __convert_to_field_data(
        response: List[EmbeddedVectors], meta: dict = None
    ) -> List[dict]:
        # Return a list of dicts matching the schema (excluding auto_id "id")
        meta_json = json.dumps(meta) if meta else "{}"
        return [
            {
                "chunk": e.chunk,
                "model": e.model.lower(),
                "vector": e.vector,
                "meta": meta_json,  # Add meta as JSON string
            }
            for e in response
        ]

    def insert_data(self, vector: List[EmbeddedVectors], **kwargs: Any) -> None:
        try:
            for i, e in enumerate(vector):
                logger.debug(f"Item {i}: vector length = {len(e.vector)}")
            logger.debug(
                f"Inserting {len(vector)} vectors into Milvus collection '{self._store_name}'"
            )
            if self.__set_collection() is False:
                raise Exception(f"Failed to set collection for {self._store_name}")

            client = self._get_tenant_client()
            logger.debug(
                f"Inserting {len(vector)} vectors into Milvus collection '{self._store_name}'"
            )
            # logger.debug(f"Insert data: {self._convert_to_field_data(vector)}")
            client.insert(
                collection_name=self._store_name,
                data=self.__convert_to_field_data(vector, meta=kwargs),
                partition_name=kwargs.get("partition_name", ""),
            )
            logger.debug(
                f"Successfully inserted {len(vector)} vectors into Milvus collection '{self._store_name}'"
            )
            client.flush(self._store_name)
        except Exception as ex:
            logger.error(f"Error inserting data into Milvus collection: {ex}")
            raise Exception("Error inserting data into Milvus collection") from ex

    def search_embedded_data(
        self, text_to_search: str, vector: List[float], parameters: dict
    ) -> dict:
        try:
            results = self.search_store(vector, parameters)
            if results:
                return {
                    "status": "OK",
                    "results": results,
                    "message": f"Found matching chunk for text '{text_to_search}'",
                }
            else:
                return {
                    "status": "no chunks found",
                    "message": f"Could not find any matching chunk for text '{text_to_search}'",
                }
        except Exception as ex:
            logger.error(f"Exception during search: {ex}")
            return {"status": "Exception", "message": str(ex)}

    def search_store(self, vector: List[float], parameters: dict) -> List[Any]:
        if self.__set_collection() is False:
            raise Exception(f"Failed to set collection for {self._store_name}")
        results: List[Any] = []
        client = self._get_tenant_client()

        model = parameters.get("model", "").lower()
        expr = f'model == "{model}"' if model else ""
        # HINT: Ensure search_params matches your collection schema and Milvus requirements
        search_params = {
            "metric_type": parameters.get("metric_type", "COSINE"),
            "params": {"nprobe": parameters.get("nprobe", 10)},
            "limit": parameters.get("limit", 10),
            "output_fields": ["chunk"],
            "expr": expr,
        }

        result = client.search(
            collection_name=self._store_name,
            data=[vector],
            anns_field="vector",
            search_params=search_params,
            limit=search_params["limit"],
            output_fields=search_params["output_fields"],
        )
        # Parse results as needed
        for hits in result:
            for hit in hits:
                chunk = hit.entity.get("chunk")
                if chunk:
                    results.append(json.loads(chunk))
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
                BaseMilvus._create_vector_store_index_if_not_exists(
                    self._store_name, self._tenant_code
                )
                client.load_collection(self._store_name)
            else:
                logger.info(
                    f"Vector store '{self._store_name}' does not exist. so create it."
                )
                BaseMilvus._setup_tenant_vector_store(
                    tenant_code=self._tenant_code,
                    user_id=self._user_id,
                    vector_dimension=self._vector_dimension,
                )
                # try:
                #     with self._lock:
                #         # make sure to use the admin client to create the collection
                #         logger.info(
                #             f"Creating vector store '{self._store_name}' for tenant '{self._tenant_code}'"
                #         )
                #         self._get_store_admin_client().create_collection(
                #             collection_name=self._store_name,
                #             schema=BaseMilvus._get_vector_store_schema(
                #                 self._store_name
                #             ),
                #         )
                #         BaseMilvus._create_vector_store_index_if_not_exists(
                #             self._store_name
                #         )
                #         tenant_role_name = (
                #             BaseMilvus._get_tenant_role_name_by_tenant_code(
                #                 self._tenant_code
                #             )
                #         )
                #         BaseMilvus._grant_tenant_privileges_to_collection_if_missing(
                #             tenant_role_name, self._store_name
                #         )
                #         logger.info(
                #             f"Vector store '{self._store_name}' created successfully."
                #         )
                #         return True
                # except Exception as ex:
                #     logger.error(
                #         f"Failed to create collection '{self._store_name}': {ex}"
                #     )
                #     raise Exception(
                #         f"Failed to create collection '{self._store_name}': {ex}"
                #     )
        except Exception as ex:
            logger.error(f"Error in _set_collection for '{self._store_name}': {ex}")
            raise Exception(f"Error in _set_collection for '{self._store_name}': {ex}")

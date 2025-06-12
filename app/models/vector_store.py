import json
from threading import Lock
from typing import Any, List, Optional

from pymilvus import Collection, MilvusClient  # Adjust if needed

from app.app_init import APP_SETTINGS
from app.logger import get_logger
from app.models.base_milvus import BaseMilvus
from app.models.embeded_vectors import EmbeddedVectors

logger = get_logger("VectorStore")


class VectorStore(BaseMilvus):
    def __init__(self, tenant_code: str, user_id: str, password: str):
        self._tenant_code: str = tenant_code
        self._user_id: str = user_id
        self._password: str = password
        self._tenant_role_name: str = BaseMilvus._get_tenant_role_name_by_tenant_code(
            tenant_code
        )
        self._db_name: str = BaseMilvus._get_db_name_by_tenant_code(tenant_code)
        self._store_name: str = BaseMilvus._get_vector_store_name_by_tenant_code(
            self._tenant_code
        )
        self._tenant_client: Optional[MilvusClient] = None
        self._lock: Lock = Lock()

    def _get_tenant_client(self) -> MilvusClient:
        with self._lock:
            if self._tenant_client is None:
                # HINT: Ensure APP_SETTINGS is loaded before this call
                self._tenant_client = MilvusClient(
                    host=APP_SETTINGS.app.vector_store.host,
                    port=APP_SETTINGS.app.vector_store.port,
                    user=self._user_id,
                    password=self._password,
                    database=self._db_name,
                )
            return self._tenant_client

    @staticmethod
    def _convert_to_field_data(response: List[EmbeddedVectors]) -> List[list]:
        # HINT: Order of fields must match Milvus schema
        return [
            [e.content for e in response],
            [e.model_used.lower() for e in response],
            [e.vectors for e in response],
        ]

    def insert_data(self, vectors: List[EmbeddedVectors]) -> None:
        try:
            if self._set_collection() is False:
                raise Exception(f"Failed to set collection for {self._store_name}")

            client = self._get_tenant_client()
            client.insert(
                collection_name=self._store_name,
                data=self._convert_to_field_data(vectors),
            )
            self.admin_client.flush([self._store_name])
        except Exception as ex:
            logger.error(f"Error inserting data into Milvus collection: {ex}")
            raise Exception("Error inserting data into Milvus collection") from ex

    def search_embedded_data(
        self, text_to_search: str, vectors: List[float], parameters: dict
    ) -> dict:
        try:
            results = self.search_store(vectors, parameters)
            if results:
                return {
                    "status": "OK",
                    "results": results,
                    "message": f"Found matching content for text '{text_to_search}'",
                }
            else:
                return {
                    "status": "NoContent",
                    "message": f"Could not find any matching content for text '{text_to_search}'",
                }
        except Exception as ex:
            logger.error(f"Exception during search: {ex}")
            return {"status": "Exception", "message": str(ex)}

    def search_store(self, vectors: List[float], parameters: dict) -> List[Any]:
        if self._set_collection() is False:
            raise Exception(f"Failed to set collection for {self._store_name}")
        results: List[Any] = []
        client = self._get_tenant_client()

        model_to_use = parameters.get("model_to_use", "").lower()
        expr = f'modelused == "{model_to_use}"' if model_to_use else ""
        # HINT: Ensure search_params matches your collection schema and Milvus requirements
        search_params = {
            "metric_type": parameters.get("metric_type", "COSINE"),
            "params": {"nprobe": parameters.get("nprobe", 10)},
            "limit": parameters.get("limit", 10),
            "output_fields": ["content"],
            "expr": expr,
        }

        result = client.search(
            collection_name=self._store_name,
            data=[vectors],
            anns_field="vector",
            search_params=search_params,
            limit=search_params["limit"],
            output_fields=search_params["output_fields"],
        )
        # Parse results as needed
        for hits in result:
            for hit in hits:
                content = hit.entity.get("content")
                if content:
                    results.append(json.loads(content))
        return results

    def _set_collection(self) -> bool:
        """
        Gets the collection for this tenant, creating it (and its index/privileges) if it does not exist.
        Handles and logs errors if collection creation fails.
        Uses a lock to ensure thread safety during collection creation.
        """
        try:
            with self._lock:  # HINT: Lock to avoid race condition during collection creation
                client = self._get_tenant_client()
                if client.has_collection(self._store_name):
                    client.load_collection(self._store_name)
                    logger.info(
                        f"Vector store '{self._store_name}' already exists and loaded"
                    )
                else:
                    try:
                        with self._base_lock:
                            self.admin_client.create_collection(
                                self._store_name,
                                BaseMilvus._get_vector_store_schema(self._store_name),
                            )
                            BaseMilvus._create_vector_store_index_if_not_exists(
                                self._store_name
                            )
                            tenant_role_name = (
                                BaseMilvus._get_tenant_role_name_by_tenant_code(
                                    self._tenant_code
                                )
                            )
                            BaseMilvus._grant_tenant_privileges_to_collection_if_missing(
                                tenant_role_name, self._store_name
                            )
                            logger.info(
                                f"Vector store '{self._store_name}' created successfully."
                            )
                            return True
                    except Exception as ex:
                        logger.error(
                            f"Failed to create collection '{self._store_name}': {ex}"
                        )
                        raise Exception(
                            f"Failed to create collection '{self._store_name}': {ex}"
                        )
        except Exception as ex:
            logger.error(f"Error in _set_collection for '{self._store_name}': {ex}")
            raise Exception(f"Error in _set_collection for '{self._store_name}': {ex}")

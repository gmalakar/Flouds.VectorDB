from threading import Lock
from typing import Any, List, Optional

from pymilvus import CollectionSchema, DataType, FieldSchema, MilvusClient
from pymilvus.milvus_client.index import IndexParams

from app.logger import get_logger

logger = get_logger("BaseMilvus")


class BaseMilvus:
    _COLLECTION_SCHEMA_NAME = "vector_store_schema"  # HINT: Now 'private' by convention
    _DB_NAME_SUFFIX = "_vectorstore"
    _TENANT_NAME_SUFFIX = "_tenant_role"
    _TENANT_ROLE_PRIVILEGES: List[str] = ["Insert", "Search", "Query"]
    _base_lock: Lock = Lock()  # HINT: Class-level lock for shared access

    def __init__(self):
        self._admin_client: MilvusClient = None

    @property
    def admin_client(self) -> MilvusClient:
        return self._admin_client

    @admin_client.setter
    def admin_client(self, value: MilvusClient):
        self._admin_client = value

    @classmethod
    def get_collection_schema_name(cls) -> str:
        return cls._COLLECTION_SCHEMA_NAME

    @staticmethod
    def _get_tenant_role_name_by_tenant_code(tenant_code: str) -> str:
        return f"{tenant_code.lower()}{BaseMilvus._TENANT_NAME_SUFFIX}"

    @staticmethod
    def _get_db_name_by_tenant_code(tenant_code: str) -> str:
        return f"{tenant_code.lower()}{BaseMilvus._DB_NAME_SUFFIX}"

    @staticmethod
    def _get_vector_store_name_by_tenant_code(tenant_code: str) -> str:
        return f"{BaseMilvus._COLLECTION_SCHEMA_NAME}_for_{tenant_code.lower()}".lower()

    @staticmethod
    def _get_vector_store_schema(name: str, dimension: int = 256) -> CollectionSchema:
        fields = [
            FieldSchema(
                name="id",
                dtype=DataType.INT64,
                is_primary=True,
                auto_id=True,
                description="Primary key",
            ),
            FieldSchema(
                name="content",
                dtype=DataType.VARCHAR,
                max_length=60535,
                description="Text",
            ),
            FieldSchema(
                name="modelused",
                dtype=DataType.VARCHAR,
                max_length=50,
                description="model used",
            ),
            FieldSchema(
                name="vector",
                dtype=DataType.FLOAT_VECTOR,
                dim=dimension,
                description="Vector of The content",
            ),
        ]
        return CollectionSchema(
            name=name,
            fields=fields,
            description="A collection for storing vectors of a document along with document's meta data",
        )

    @staticmethod
    def _create_index_if_missing(
        collection_name: str, index_params: dict, index_name: str
    ):
        """
        Creates an index on a collection field only if it doesn't already exist.
        """
        try:
            indexes = BaseMilvus.admin_client.list_indexes(
                collection_name=collection_name
            )
            existing = {idx["index_name"] for idx in indexes}
            field_name = index_params["field_name"]

            if index_name not in existing:
                # Convert dict to IndexParams
                ip = IndexParams()
                ip.add_index(
                    field_name=index_params["field_name"],
                    index_type=index_params["index_type"],
                    index_name=index_params["index_name"],
                    metric_type=index_params["metric_type"],
                    params=index_params["params"],
                )
                BaseMilvus.admin_client.create_index(
                    collection_name=collection_name, index_params=ip
                )
                logger.debug(
                    f"Index '{index_name}' created on '{field_name}' in '{collection_name}'."
                )
            else:
                logger.debug(
                    f"Index '{index_name}' already exists on '{collection_name}'."
                )
        except Exception as e:
            logger.error(f"Failed to create index '{index_name}': {e}")
            raise Exception(f"Failed to create index '{index_name}': {e}")

    @staticmethod
    def _create_vector_store_index_if_not_exists(collection_name: str):
        index_name = "vector_index"
        try:
            index_params = {
                "field_name": "vector",
                "index_type": "IVF_FLAT",
                "metric_type": "COSINE",
                "params": {"nlist": 1024},
                "index_name": index_name,
            }
            BaseMilvus._create_index_if_missing(
                collection_name,
                index_params,
                index_name=index_name,
            )
        except Exception as e:
            logger.error(f"cannot create index '{index_name}': {e}")
            raise Exception(f"Failed to create index '{index_name}': {e}")

    @staticmethod
    def _grant_tenant_privileges_to_collection_if_missing(
        role_name: str, object_name: str
    ) -> bool:
        """
        Grants privileges on a Milvus database to a role only if they aren't already granted.

        Args:
            role_name: Name of the role to grant privileges to.
            database_name: Name of the target database.
            privileges: List of privilege names to grant (e.g. ["Use", "CreateCollection"]).
        """
        try:
            for privilege in BaseMilvus._TENANT_ROLE_PRIVILEGES:
                BaseMilvus.admin_client.grant_privilege(
                    role_name=role_name,
                    object_type="Collection",
                    privilege=privilege,
                    object_name=object_name,
                )
                logger.debug(
                    f"Granted '{privilege}' on Collection '{object_name}' to role '{role_name}'"
                )
            return True
        except Exception as e:
            logger.error(f"[!] Error while granting database privileges: {e}")
            raise Exception(f"Failed to grant privileges: {e}")

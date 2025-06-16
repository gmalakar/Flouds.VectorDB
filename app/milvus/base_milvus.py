# =============================================================================
# File: base_milvus.py
# Date: 2025-06-14
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import base64
import os
import random
import re
import string
import uuid
from functools import lru_cache
from threading import Lock
from typing import Any, List, Optional

from pymilvus import (
    CollectionSchema,
    DataType,
    FieldSchema,
    MilvusClient,
    MilvusException,
    connections,
)
from pymilvus.milvus_client.index import IndexParams

from app.app_init import APP_SETTINGS
from app.logger import get_logger
from app.modules.concurrent_dict import ConcurrentDict

logger = get_logger("BaseMilvus")


class BaseMilvus:
    """
    Base class for Milvus operations, including connection management,
    user/role/collection/index setup, and utility helpers.
    """

    __tenant_connections: ConcurrentDict = ConcurrentDict("_tenant_connections")
    __COLLECTION_SCHEMA_NAME: str = "vector_store_schema"
    __DB_NAME_SUFFIX: str = "_vectorstore"
    __TENANT_NAME_SUFFIX: str = "_tenant_role"
    __CLIENT_ID_LENGTH: int = 32
    __CLIENT_SECRET_LENGTH: int = 36
    __TENANT_ROLE_PRIVILEGES: List[str] = [
        "CreateIndex",
        "Search",
        "Insert",
        "Load",
        "Release",
        "Query",
        "Flush",
        "Compaction",
    ]
    __init_lock: Lock = Lock()
    __initialized: bool = False
    __milvus_endpoint: str = "localhost"
    __milvus_port: int = 19530
    __milvus_admin_username: str = "none"
    __milvus_admin_password: str = "none"
    __minvus_admin_client: Optional[MilvusClient] = None
    __db_switch_lock: Lock = Lock()
    __user_create_lock: Lock = Lock()

    def __init__(self) -> None:
        """
        Initializes the BaseMilvus instance and ensures global initialization.
        """
        logger.debug("Initializing BaseMilvus...")
        BaseMilvus.initialize()
        self._lock: Lock = Lock()

    @staticmethod
    def __get_uri(host: str, port: int) -> str:
        """
        Concatenates host and port to return a URI string.
        Example: host='milvus-standalone', port=19530 -> 'milvus-standalone:19530'
        """
        return f"{host}:{port}"

    @classmethod
    def initialize(cls) -> None:
        """
        Initializes the Milvus admin client and sets configuration.
        """
        with cls.__init_lock:
            if not cls.__initialized:
                username = (
                    os.getenv("VECTORDB_USERNAME") or APP_SETTINGS.vectordb.username
                )
                if not username or username.strip() == "":
                    raise ValueError(
                        "vectordb.username is missing! Set VECTORDB_USERNAME env or in your config."
                    )
                cls.__milvus_admin_username = username
                logger.info(f"Using Milvus username: {cls.__milvus_admin_username}")
                password = (
                    os.getenv("VECTORDB_PASSWORD") or APP_SETTINGS.vectordb.password
                )
                if not password or password.strip() == "":
                    raise ValueError(
                        "vectordb.password is missing! Set VECTORDB_PASSWORD env or in your config."
                    )
                cls.__milvus_admin_password = password

                # Validate and set endpoint and port
                endpoint = (
                    os.getenv("VECTORDB_ENDPOINT") or APP_SETTINGS.vectordb.endpoint
                )
                # If running in Docker and endpoint does not start with protocol, add protocol
                if not re.match(r"^https?://", endpoint):
                    endpoint = f"http://{endpoint}"
                if (
                    endpoint
                    and isinstance(endpoint, str)
                    and re.match(r"^https?://|^[\w\.-]+$", endpoint)
                ):
                    cls.__milvus_endpoint = endpoint
                else:
                    raise ValueError(
                        "vectordb.endpoint is invalid! Must be a valid URL or hostname. Set VECTORDB_ENDPOINT env or in your config."
                    )
                port = os.getenv("VECTORDB_PORT") or APP_SETTINGS.vectordb.port
                try:
                    port = int(port)
                except Exception:
                    port = 19530
                if port and port > 0:
                    cls.__milvus_port = port
                    logger.debug(f"Using Milvus port: {cls.__milvus_port}")
                else:
                    logger.warning(
                        "vectordb.port is invalid! Using default port 19530."
                    )
                cls.__admin_role_name = APP_SETTINGS.vectordb.admin_role_name
                logger.info(f"Using Milvus admin role name: {cls.__admin_role_name}")

                logger.info(f"Using Milvus endpoint: {cls.__milvus_endpoint}")
                # create internal client
                cls.__minvus_admin_client = MilvusClient(
                    uri=cls._get_milvus_url(),
                    user=cls.__milvus_admin_username,
                    password=cls.__milvus_admin_password,
                )
                try:
                    # HINT: Try a simple operation to verify connection
                    if not cls.check_connection(cls.__minvus_admin_client):
                        logger.error("Milvus connection failed!")
                        raise ConnectionError(
                            "Failed to connect to Milvus. Please check your configuration."
                        )
                except Exception as ex:
                    logger.error(f"Failed to connect to Milvus: {ex}")
                    raise ConnectionError(f"Failed to connect to Milvus: {ex}")
                cls.__initialized = True

    @staticmethod
    def _get_milvus_url() -> str:
        """
        Returns the Milvus server URL using the configured endpoint and port.
        """
        return f"{BaseMilvus.__milvus_endpoint}:{BaseMilvus.__milvus_port}"

    @staticmethod
    def __assign_role_to_user(user_name: str, role_name: str) -> None:
        """
        Assigns a role to a user if the assignment doesn't already exist.
        """
        admin_client = BaseMilvus.__get_internal_admin_client()
        try:
            user_info = admin_client.describe_user(user_name=user_name)
            logger.debug(f"user_info for '{user_name}': {user_info}")
            roles = user_info.get("roles", [])
            # If roles is a list of strings:
            if roles and isinstance(roles[0], str):
                current_roles = set(roles)
            # If roles is a list of dicts:
            elif roles and isinstance(roles[0], dict):
                current_roles = {role.get("role_name", "") for role in roles}
            else:
                current_roles = set()

            if role_name not in current_roles:
                admin_client.grant_role(user_name=user_name, role_name=role_name)
                logger.debug(f"Assigned role '{role_name}' to user '{user_name}'.")
            else:
                logger.debug(f"User '{user_name}' already has role '{role_name}'.")
        except Exception as e:
            logger.error(f"Failed to assign role: {e}")
            raise Exception(
                f"Failed to assign role '{role_name}' to user '{user_name}': {e}"
            )

    @staticmethod
    def _set_admin_role_if_not_exists() -> bool:
        """
        Ensures the admin role exists and has all necessary privileges.
        Returns True if created, False if already existed.
        """
        try:
            new = BaseMilvus._create_role_if_not_exists(
                APP_SETTINGS.vectordb.admin_role_name
            )
            if new:
                logger.info(
                    f"Admin role '{APP_SETTINGS.vectordb.admin_role_name}' created successfully."
                )
                BaseMilvus.__assign_role_to_user(
                    user_name=APP_SETTINGS.vectordb.admin_role_name,
                    role_name=APP_SETTINGS.vectordb.admin_role_name,
                )
                # This gives full access across all collections and databases.
                BaseMilvus.__get_internal_admin_client().grant_privilege(
                    role_name=APP_SETTINGS.vectordb.admin_role_name,
                    object_type="Global",
                    privilege="*",
                    object_name="*",
                )
            BaseMilvus.__get_internal_admin_client().grant_privilege_v2(
                role_name=APP_SETTINGS.vectordb.admin_role_name,
                privilege="SelectOwnership",
                collection_name="*",
                db_name="default",
            )

            BaseMilvus.__get_internal_admin_client().grant_privilege_v2(
                role_name="admin",
                privilege="SelectOwnership",
                collection_name="*",
                db_name="default",
            )

        except Exception as ex:
            logger.error(f"Error setting up Milvus admin role: {ex}")
            raise ConnectionError(f"Error setting up Milvus admin role: {ex}")

    @staticmethod
    def _create_role_if_not_exists(role_name: str) -> bool:
        """
        Checks if the tenant role exists, creates it if not.
        Returns True if created, False if already existed.
        """
        client = BaseMilvus.__get_internal_admin_client()
        try:
            existing_roles = client.list_roles()
            if role_name not in existing_roles:
                client.create_role(role_name=role_name)
                logger.debug(f"Role '{role_name}' created successfully!")
                return True
            else:
                logger.debug(f"Role '{role_name}' already exists.")
            return False
        except Exception as ex:
            logger.error(f"cannot create role '{role_name}': {ex}")
            raise Exception(f"Failed to create role '{role_name}': {ex}")

    @classmethod
    def __get_internal_admin_client(cls) -> MilvusClient:
        """
        Returns the internal admin MilvusClient, initializing if necessary.
        """
        if not cls.__initialized:
            if (
                cls.__minvus_admin_client is None
            ):  # HINT: Check if the client is already initialized
                # create internal client
                cls.__minvus_admin_client = MilvusClient(
                    uri=cls._get_milvus_url(),
                    user=cls.__milvus_admin_username,
                    password=cls.__milvus_admin_password,
                )
        else:
            logger.debug(f"Initialized: Milvus admin client already exists")
        return cls.__minvus_admin_client

    @classmethod
    def _get_collection_schema_name(cls) -> str:
        """
        Returns the collection schema name.
        """
        return cls.__COLLECTION_SCHEMA_NAME

    @staticmethod
    def _get_tenant_role_name_by_tenant_code(tenant_code: str) -> str:
        """
        Returns the role name for a given tenant code.
        """
        return f"{tenant_code.lower()}{BaseMilvus.__TENANT_NAME_SUFFIX}"

    @staticmethod
    def _get_db_name_by_tenant_code(tenant_code: str) -> str:
        """
        Returns the database name for a given tenant code.
        """
        return f"{tenant_code.lower()}{BaseMilvus.__DB_NAME_SUFFIX}"

    @staticmethod
    def _get_vector_store_name_by_tenant_code(tenant_code: str) -> str:
        """
        Returns the vector store (collection) name for a given tenant code.
        """
        return (
            f"{BaseMilvus.__COLLECTION_SCHEMA_NAME}_for_{tenant_code.lower()}".lower()
        )

    @staticmethod
    def __generate_client_id(current_client_id: str, tenant_code: str) -> str:
        """
        Returns a valid client_id. If current_client_id does not start with tenant_code-
        or its length does not match total_length, generate a new one with tenant_code- as prefix.
        """
        tenant_code = tenant_code.lower()
        prefix = f"{tenant_code}_"
        total_length = BaseMilvus.__CLIENT_ID_LENGTH
        if (
            not current_client_id
            or not current_client_id.lower().startswith(prefix)
            or len(current_client_id) != total_length
        ):
            # Generate a new client_id with tenant_code- as prefix
            letters = string.ascii_uppercase + string.digits
            suffix_length = total_length - len(prefix)
            suffix = "".join(random.choice(letters) for _ in range(suffix_length))
            return prefix + suffix
        return current_client_id

    @staticmethod
    def __generate_secret_key(current_secret_key: str) -> str:
        """
        Generates a new urlsafe secret key if the current one is invalid.
        """
        size = BaseMilvus.__CLIENT_SECRET_LENGTH
        # Generate a new urlsafe key to get the expected length
        expected_length = len(
            base64.urlsafe_b64encode(os.urandom(size)).decode("utf-8")
        )

        def is_urlsafe_base64(s: str) -> bool:
            return re.fullmatch(r"^[A-Za-z0-9_\-]+={0,2}$", s) is not None

        if (
            not current_secret_key
            or len(current_secret_key) != expected_length
            or not is_urlsafe_base64(current_secret_key)
        ):
            return base64.urlsafe_b64encode(os.urandom(size)).decode("utf-8")
        return current_secret_key

    @staticmethod
    def _validate_token(token: str) -> bool:
        """
        Validates a Milvus token by attempting a connection.
        Returns True if valid, False otherwise.
        """
        logger.debug(f"Validating token: {token}")
        try:
            alias = str(uuid.uuid4())  # Generate a unique alias
            connections.connect(
                uri=BaseMilvus._get_milvus_url(), token=token, alias=alias
            )
            logger.debug(f"Token '{token}' validated successfully.")
            connections.disconnect(alias)
            return True
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            return False

    @staticmethod
    def _get_current_user_of_a_tenant(tenant_code: str) -> Optional[str]:
        """
        Returns the current user for a tenant, or None if not found.
        """
        current_user = None
        admin_client = BaseMilvus.__get_internal_admin_client()
        existing_users = admin_client.list_users()
        matching_users = [
            item
            for item in existing_users
            if item.startswith(tenant_code.lower() + "_")
        ]

        if matching_users is not None and len(matching_users) > 0:
            current_user = matching_users[0]
        return current_user

    @staticmethod
    def _create_user_for_tenant(tenant_code: str, **kwargs: Any) -> dict:
        """
        Creates a user if it does not exist. Returns a summary dict.
        Thread-safe.
        """
        summary = {
            "tenant_code": tenant_code,
            "client_id": None,
            "client_secret": None,
            "existing_user": False,
            "message": "New User created successfully.",
        }
        admin_client = BaseMilvus.__get_internal_admin_client()
        current_user = BaseMilvus._get_current_user_of_a_tenant(tenant_code)
        if current_user is not None:
            summary["existing_user"] = True
            summary["client_id"] = current_user
            summary["message"] = (
                f"User '{current_user}' already exists for tenant '{tenant_code}'."
            )
            return summary
        else:
            # Generate a new user name
            with BaseMilvus.__user_create_lock:
                try:
                    # HINT: Ensure client_id and secret_key are provided
                    client_id = BaseMilvus.__generate_client_id("none", tenant_code)
                    secret_key = BaseMilvus.__generate_secret_key("none")
                    admin_client.create_user(user_name=client_id, password=secret_key)
                    summary["existing_user"] = False
                    summary["client_secret"] = secret_key
                    summary["client_id"] = client_id
                    logger.debug(f"User '{client_id}' created successfully!")
                except Exception as ex:
                    logger.error(f"Failed to create user '{client_id}': {ex}")
                    summary["message"] = f"Failed to create user '{client_id}': {ex}"
        return summary

    @staticmethod
    def _get_tenant_client(
        tenant_client_id: str, tenant_client_secret: str, tenant_database: str
    ) -> MilvusClient:
        """
        Returns a MilvusClient for the given tenant credentials.
        """
        logger.debug(
            f"host: {BaseMilvus.__milvus_endpoint}, port: {BaseMilvus.__milvus_port} - Creating MilvusClient for tenant: {tenant_client_id}, database: {tenant_database}"
        )
        return MilvusClient(
            uri=BaseMilvus._get_milvus_url(),
            user=tenant_client_id,
            password=tenant_client_secret,
            database=tenant_database,
        )

    @staticmethod
    def get_chunk_meta_output_fields() -> list:
        """
        Returns a list specifying output fields for chunk and meta.
        """
        return ["chunk", "meta"]

    @staticmethod
    def _get_vector_store_schema(name: str, dimension: int = 256) -> CollectionSchema:
        """
        Returns the collection schema for a vector store.
        """
        fields = [
            FieldSchema(
                name="id",
                dtype=DataType.INT64,
                is_primary=True,
                auto_id=True,
                description="Primary key",
            ),
            FieldSchema(
                name="chunk",
                dtype=DataType.VARCHAR,
                max_length=60535,
                description="Text chunk",
            ),
            FieldSchema(
                name="model",
                dtype=DataType.VARCHAR,
                max_length=256,
                description="Model used for embedding (e.g., 'openai', 'cohere', etc.)",
            ),
            FieldSchema(
                name="vector",
                dtype=DataType.FLOAT_VECTOR,
                dim=dimension,
                description="Vector of the chunk",
            ),
            FieldSchema(
                name="meta",
                dtype=DataType.VARCHAR,  # Or DataType.JSON if supported
                max_length=4096,  # Adjust as needed
                description="Extra metadata as JSON string",
            ),
        ]
        return CollectionSchema(
            name=name,
            fields=fields,
            description="A collection for storing vectors of a document along with document's meta data",
            enable_dynamic_field=True,  # <-- Enable dynamic fields here
        )

    @staticmethod
    def __create_index_if_missing(
        collection_name: str,
        index_params: dict,
        index_name: str,
        milvus_client: Optional[MilvusClient] = None,
    ) -> None:
        """
        Creates an index on a collection field only if it doesn't already exist.
        """
        try:
            client = milvus_client or BaseMilvus.__get_internal_admin_client()
            indexes = client.list_indexes(collection_name=collection_name)
            # Fix: handle both dict and string
            existing = set()
            for idx in indexes:
                if isinstance(idx, dict) and "index_name" in idx:
                    existing.add(idx["index_name"])
                elif isinstance(idx, str):
                    existing.add(idx)

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
                client.create_index(collection_name=collection_name, index_params=ip)
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
    def _create_vector_store_index_if_not_exists(
        collection_name: str, tenant_code: str
    ) -> bool:
        """
        Creates the index for the given collection in the tenant's database if it does not exist.
        Returns True if created, False if already exists.
        Raises Exception on error.
        """
        index_name = "vector_index"
        try:
            with BaseMilvus.__db_switch_lock:
                db_admin_client = BaseMilvus._get_or_create_tenant_connection(
                    tenant_code
                )
                index_params = {
                    "field_name": "vector",
                    "index_type": "IVF_FLAT",
                    "metric_type": "COSINE",
                    "params": {"nlist": 1024},
                    "index_name": index_name,
                }
                # Check if index exists
                indexes = db_admin_client.list_indexes(collection_name=collection_name)
                existing = set()
                for idx in indexes:
                    if isinstance(idx, dict) and "index_name" in idx:
                        existing.add(idx["index_name"])
                    elif isinstance(idx, str):
                        existing.add(idx)

                if index_name not in existing:
                    ip = IndexParams()
                    ip.add_index(
                        field_name=index_params["field_name"],
                        index_type=index_params["index_type"],
                        index_name=index_params["index_name"],
                        metric_type=index_params["metric_type"],
                        params=index_params["params"],
                    )
                    db_admin_client.create_index(
                        collection_name=collection_name, index_params=ip
                    )
                    logger.debug(
                        f"Index '{index_name}' created on 'vector' in '{collection_name}'."
                    )
                    created = True
                else:
                    logger.debug(
                        f"Index '{index_name}' already exists on '{collection_name}'."
                    )
                    created = False

            return created

        except Exception as e:
            logger.error(
                f"Cannot create index '{index_name}' for tenant '{tenant_code}': {e}"
            )
            raise Exception(
                f"Failed to create index '{index_name}' for tenant '{tenant_code}': {e}"
            )

    @staticmethod
    def _grant_tenant_privileges_to_collection_if_not_exists(
        tenant_code: str, object_name: str, role_name: Optional[str] = None
    ) -> bool:
        """
        Grants privileges on a Milvus collection to a role for a specific tenant's database.
        Returns True if any privilege was newly granted, False if all already existed.
        Raises Exception on error.
        """
        try:
            db_name = BaseMilvus._get_db_name_by_tenant_code(tenant_code)
            admin_client = BaseMilvus.__get_internal_admin_client()
            db_list = admin_client.list_databases()
            if db_name not in db_list:
                logger.error(
                    f"Database '{db_name}' does not exist for tenant '{tenant_code}'."
                )
                raise Exception(
                    f"Database '{db_name}' does not exist for tenant '{tenant_code}'."
                )

            with BaseMilvus.__db_switch_lock:
                db_admin_client = BaseMilvus._get_or_create_tenant_connection(
                    tenant_code
                )

                # Use provided role_name or default to admin role
                if not role_name:
                    role_name = BaseMilvus.__admin_role_name

                granted_any = False
                for privilege in BaseMilvus.__TENANT_ROLE_PRIVILEGES:
                    db_admin_client.grant_privilege(
                        role_name=role_name,
                        object_type="Collection",
                        privilege=privilege,
                        object_name=object_name,
                    )
                    logger.debug(
                        f"Granted '{privilege}' on Collection '{object_name}' in DB '{db_name}' to role '{role_name}'"
                    )
                    granted_any = True

            return granted_any

        except Exception as e:
            logger.error(f"[!] Error while granting collection privileges: {e}")
            raise Exception(f"Failed to grant privileges: {e}")

    @staticmethod
    def check_connection(client) -> bool:
        """
        Returns True if the internal admin client can connect to Milvus and list collections, False otherwise.
        """
        if client is None:
            logger.error("Milvus admin client is not initialized.")
            return False
        try:
            client.list_collections(timeout=2)  # Set a timeout for the operation
            logger.info("Milvus connection is healthy.")
            return True
        except Exception as ex:
            logger.error(f"Milvus connection check failed: {ex}")
            return False

    @staticmethod
    def _create_vector_store_collection_if_not_exists(
        tenant_code: str,
        vector_dimension: int,
    ) -> bool:
        """
        Creates the vector store collection for the tenant if it does not exist.
        Returns True if created, False if already exists.
        Raises Exception on error.
        """
        try:
            db_name = BaseMilvus._get_db_name_by_tenant_code(tenant_code)
            collection_name = BaseMilvus._get_vector_store_name_by_tenant_code(
                tenant_code
            )
            admin_client = BaseMilvus.__get_internal_admin_client()
            db_list = admin_client.list_databases()
            if db_name not in db_list:
                logger.error(
                    f"Database '{db_name}' does not exist for tenant '{tenant_code}'."
                )
                raise Exception(
                    f"Database '{db_name}' does not exist for tenant '{tenant_code}'."
                )

            with BaseMilvus.__db_switch_lock:
                db_admin_client = BaseMilvus._get_or_create_tenant_connection(
                    tenant_code
                )
                collections = db_admin_client.list_collections()
                if collection_name not in collections:
                    if vector_dimension <= 0:
                        vector_dimension = (
                            APP_SETTINGS.vectordb.default_dimension
                        )  # Default to configured dimension if not provided
                    logger.info(
                        f"Creating collection '{collection_name}' in database '{db_name}' for tenant '{tenant_code}' and dimension {vector_dimension}."
                    )
                    db_admin_client.create_collection(
                        collection_name=collection_name,
                        schema=BaseMilvus._get_vector_store_schema(
                            name=collection_name, dimension=vector_dimension
                        ),
                    )
                    logger.info(f"Collection '{collection_name}' created successfully.")
                    created = True
                else:
                    logger.info(
                        f"Collection '{collection_name}' already exists in database '{db_name}'."
                    )
                    created = False

            return created

        except Exception as ex:
            logger.error(
                f"Failed to create collection '{collection_name}' for tenant '{tenant_code}': {ex}"
            )
            raise Exception(
                f"Failed to create collection '{collection_name}' for tenant '{tenant_code}': {ex}"
            )

    @staticmethod
    def _is_super_user(user_id: str) -> bool:
        """
        Checks if the given user_id is a super user (admin/root or has admin role).
        """
        try:
            if not user_id and user_id.strip() == "":
                logger.error("User ID is empty or None.")
                return False
            if user_id.lower() == "root" or user_id.lower() == "admin":
                # If user is 'root' or 'admin', consider it a super user
                logger.debug("User is 'admin', considered super user.")
                return True
            client = BaseMilvus.__get_internal_admin_client()
            user_info = client.describe_user(user_name=user_id)
            roles = user_info.get("roles", [])
            # Handle both list of strings and list of dicts
            role_names = set()
            if roles and isinstance(roles[0], str):
                role_names = set(roles)
            elif roles and isinstance(roles[0], dict):
                role_names = {role.get("role_name", "") for role in roles}
            logger.debug(f"Roles for user '{user_id}': {role_names}")
            return (
                "admin" in role_names
                or APP_SETTINGS.vectordb.admin_role_name in role_names
            )
        except MilvusException as e:
            logger.error(f"Error checking admin role for user '{user_id}': {e}")
            return False

    @staticmethod
    def _setup_tenant_vector_store(
        tenant_code: str, vector_dimension: int = 256, **kwargs: Any
    ) -> dict[str, Any]:
        """
        Ensures the DB, collection, index, role, and privileges exist for a tenant.
        Creates the DB if it does not exist.
        Returns a dict summarizing what was created or already existed.
        """
        summary = {
            "db_created": False,
            "collection_created": False,
            "index_created": False,
            "role_created": False,
            "privileges_granted": False,
            "role_assigned": False,
            "client_id": None,
            "client_secret": None,
            "new_client_id": False,
            "rejected_client_id": False,
            "tenant_code": tenant_code,
            "message": "Tenant vector store setup completed successfully.",
        }
        try:
            db_name = BaseMilvus._get_db_name_by_tenant_code(tenant_code)
            collection_name = BaseMilvus._get_vector_store_name_by_tenant_code(
                tenant_code
            )
            role_name = BaseMilvus._get_tenant_role_name_by_tenant_code(tenant_code)
            admin_client = BaseMilvus.__get_internal_admin_client()
            db_list = admin_client.list_databases()
            if db_name not in db_list:
                admin_client.create_database(db_name)
                logger.info(f"Database '{db_name}' created for tenant '{tenant_code}'.")
                summary["db_created"] = True
            else:
                logger.info(
                    f"Database '{db_name}' already exists for tenant '{tenant_code}'."
                )

            # User creation logic (extract to helper if desired)
            current_user = BaseMilvus._get_current_user_of_a_tenant(tenant_code)
            replace_current_client_id = kwargs.get("replace_current_client_id", False)
            create_another_client_id = kwargs.get("create_another_client_id", False)
            logger.debug(
                f"Current user for tenant '{tenant_code}': {current_user}, replace_current_client_id: {replace_current_client_id}, create_another_client_id: {create_another_client_id}"
            )
            if (
                current_user is None
                or replace_current_client_id
                or create_another_client_id
            ):
                if current_user and replace_current_client_id:
                    admin_client.delete_user(user_name=current_user)
                client_id = BaseMilvus.__generate_client_id("none", tenant_code)
                secret_key = BaseMilvus.__generate_secret_key("none")
                admin_client.create_user(user_name=client_id, password=secret_key)
                summary["client_id"] = client_id
                summary["client_secret"] = secret_key
                summary["new_client_id"] = True
                logger.debug(f"User '{client_id}' created successfully!")
            else:
                summary["client_id"] = current_user
                logger.debug(f"User '{current_user}' already exists.")
            client_id = current_user

            with BaseMilvus.__db_switch_lock:
                db_admin_client = BaseMilvus._get_or_create_tenant_connection(
                    tenant_code
                )
                # 1. Collection
                collections = db_admin_client.list_collections()
                if collection_name not in collections:
                    if vector_dimension <= 0:
                        vector_dimension = APP_SETTINGS.vectordb.default_dimension
                    db_admin_client.create_collection(
                        collection_name=collection_name,
                        schema=BaseMilvus._get_vector_store_schema(
                            name=collection_name, dimension=vector_dimension
                        ),
                    )
                    logger.info(f"Collection '{collection_name}' created.")
                    summary["collection_created"] = True
                else:
                    logger.info(f"Collection '{collection_name}' already exists.")

                # 2. Index
                index_name = "vector_index"
                indexes = db_admin_client.list_indexes(collection_name=collection_name)
                existing_indexes = set()
                for idx in indexes:
                    if isinstance(idx, dict) and "index_name" in idx:
                        existing_indexes.add(idx["index_name"])
                    elif isinstance(idx, str):
                        existing_indexes.add(idx)
                if index_name not in existing_indexes:
                    ip = IndexParams()
                    ip.add_index(
                        field_name="vector",
                        index_type="IVF_FLAT",
                        index_name=index_name,
                        metric_type="COSINE",
                        params={"nlist": 1024},
                    )
                    db_admin_client.create_index(
                        collection_name=collection_name, index_params=ip
                    )
                    logger.info(f"Index '{index_name}' created on '{collection_name}'.")
                    summary["index_created"] = True
                else:
                    logger.info(
                        f"Index '{index_name}' already exists on '{collection_name}'."
                    )

                # 3. Role
                roles = db_admin_client.list_roles()
                role_names = [
                    r["role_name"] if isinstance(r, dict) else r for r in roles
                ]
                if role_name not in role_names:
                    db_admin_client.create_role(role_name=role_name)
                    logger.info(f"Role '{role_name}' created.")
                    summary["role_created"] = True
                else:
                    logger.info(f"Role '{role_name}' already exists.")

                # 4. Privileges

                granted_any = False
                for privilege in BaseMilvus.__TENANT_ROLE_PRIVILEGES:
                    db_admin_client.grant_privilege(
                        role_name=role_name,
                        object_type="Collection",
                        privilege=privilege,
                        object_name=collection_name,
                    )
                    logger.debug(
                        f"Granted '{privilege}' on Collection '{collection_name}' in DB '{db_name}' to role '{role_name}'"
                    )
                    granted_any = True
                summary["privileges_granted"] = granted_any

                # 5. Assign role to user
                users = db_admin_client.list_users()
                user_names = [
                    u["user_name"] if isinstance(u, dict) else u for u in users
                ]
                if client_id in user_names:
                    BaseMilvus.__assign_role_to_user(
                        user_name=client_id,
                        role_name=role_name,
                    )
                    logger.info(f"Assigned role '{role_name}' to user '{client_id}'.")
                    summary["role_assigned"] = True
                else:
                    logger.warning(
                        f"User '{client_id}' does not exist to assign role '{role_name}'."
                    )

            return summary

        except Exception as ex:
            logger.exception(
                f"Failed to setup vector store for tenant '{tenant_code}': {ex}"
            )
            raise Exception(
                f"Failed to setup vector store for tenant '{tenant_code}': {ex}"
            )

    @classmethod
    def _get_or_create_tenant_connection(cls, tenant_code: str) -> MilvusClient:
        """
        Gets or creates a MilvusClient instance for the given tenant/user.
        """
        db_name = cls._get_db_name_by_tenant_code(tenant_code)
        return cls.__tenant_connections.get_or_add(
            tenant_code,
            lambda: MilvusClient(
                uri=cls._get_milvus_url(),
                user=cls.__milvus_admin_username,
                password=cls.__milvus_admin_password,
                db_name=db_name,
            ),
        )

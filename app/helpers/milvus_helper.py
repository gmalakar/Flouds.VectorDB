import base64
import os
import random
import re
import string
from threading import Lock
from typing import Any, List, Optional

from pymilvus import MilvusClient

from app.logger import get_logger
from app.models.base_milvus import BaseMilvus
from app.models.embeded_vectors import EmbeddedVectors
from app.models.milvus_db_info import MilvusDBInfo
from app.models.vector_store import VectorStore
from app.modules.concurrent_dict import ConcurrentDict

logger = get_logger("milvus_helper")


class MilvusHelper(BaseMilvus):
    _init_lock: Lock = Lock()
    _initialized: bool = False
    _milvus_endpoint: str = "localhost"
    _milvus_port: int = 19530
    _milvus_admin_user: str = "admin"
    _milvus_admin_password: str = "password"
    _milvus_dimension: int = 256  # Default dimension for vectors
    _vector_stores: ConcurrentDict = ConcurrentDict("_vector_stores")
    _admin_role_name: str = "flouds_admin_role"

    @staticmethod
    def initialize(
        admin_user: str,
        admin_password: str,
        endpoint: Optional[str] = None,
        port: int = -1,
        default_dimension: int = 256,
        admin_role_name: str = "flouds_admin_role",
    ) -> None:
        """
        Initializes the Milvus admin client and sets configuration.
        """
        with MilvusHelper._init_lock:
            if not MilvusHelper._initialized:
                if not admin_user:
                    raise ValueError("admin_user is required.")
                if not admin_password:
                    raise ValueError("admin_password is required.")
                if endpoint:
                    BaseMilvus.admin_client = endpoint
                if port > 0:
                    MilvusHelper._milvus_port = port
                MilvusHelper._milvus_admin_user = admin_user
                MilvusHelper._milvus_admin_password = admin_password
                MilvusHelper._milvus_dimension = default_dimension
                MilvusHelper._admin_role_name = admin_role_name
                try:
                    BaseMilvus.admin_client = MilvusClient(
                        host=MilvusHelper._milvus_endpoint,
                        port=MilvusHelper._milvus_port,
                        user=MilvusHelper._milvus_admin_user,
                        password=MilvusHelper._milvus_admin_password,
                    )
                    # HINT: Try a simple operation to verify connection
                    BaseMilvus.admin_client.list_collections()
                    logger.info("Connected to Milvus successfully.")
                    new = MilvusHelper._create_role_if_not_exists(
                        MilvusHelper._admin_role_name
                    )
                    if new:
                        logger.info(
                            f"Admin role '{MilvusHelper._admin_role_name}' created successfully."
                        )
                        MilvusHelper._assign_role_to_user(
                            user_name=MilvusHelper._milvus_admin_user,
                            role_name=MilvusHelper._admin_role_name,
                        )
                        # This gives full access across all collections and databases.
                        BaseMilvus.admin_client.grant_privilege(
                            role_name=MilvusHelper._admin_role_name,
                            object_type="Global",
                            privilege="*",
                            object_name="*",
                        )

                except Exception as ex:
                    logger.error(f"Failed to connect to Milvus: {ex}")
                    raise ConnectionError(f"Failed to connect to Milvus: {ex}")
                MilvusHelper._initialized = True

    @staticmethod
    def insert_embedded_data(
        embedded_vectors: List[EmbeddedVectors],
        tenant_code: str,
        client_id: str,
        secret_key: str,
        tenant_db: str,
    ) -> None:
        """
        Inserts embedded vectors into the tenant's vector store.
        """
        tenant_store = MilvusHelper._get_or_add_current_volumes(
            tenant_code, client_id, secret_key
        )
        tenant_store.insert_data(embedded_vectors)

    @staticmethod
    def search_embedded_data(
        text_to_search: str, vector_to_search: List[float], parameters: dict
    ) -> Any:
        """
        Searches for embedded data in the tenant's vector store.
        """
        tenant_store = MilvusHelper._get_or_add_current_volumes(
            parameters["tenant_code"], parameters["client_id"], parameters["secret_key"]
        )
        return tenant_store.search_embedded_data(
            text_to_search, vector_to_search, parameters
        )

    @staticmethod
    def send_prompt(vector_to_search: List[float], parameters: dict) -> Any:
        """
        Searches the vector store using the given vector and parameters.
        """
        tenant_store = MilvusHelper._get_or_add_current_volumes(
            parameters["tenant_code"], parameters["client_id"], parameters["secret_key"]
        )
        return tenant_store.search_store(vector_to_search, parameters)

    @staticmethod
    def set_vector_store(
        tenant_code: str,
        vector_dimension: int,
        client_id: Optional[str],
        secret_key: Optional[str],
    ) -> MilvusDBInfo:
        """
        Sets up a vector store for a tenant, creating all necessary resources if missing.
        Uses a lock to ensure thread safety.
        """
        with MilvusHelper._init_lock:  # HINT: Lock to avoid race condition during vector store setup
            if not MilvusHelper._initialized:
                logger.error(
                    "MilvusHelper has not been initialized. Please call initialize() first."
                )
                raise Exception(
                    "Vector store has not been initialized properly. Please set required vector store values."
                )
            if not tenant_code:
                logger.error("tenant_code is required.")
                raise ValueError("tenant_code is required.")
            if vector_dimension <= 0:
                vector_dimension = (
                    MilvusHelper._milvus_dimension
                )  # Default to configured dimension if not provided

            # HINT: Create database if not exists
            db_name: str = MilvusHelper._get_db_name_by_tenant_code(tenant_code)
            MilvusHelper._create_database_if_not_exists(db_name)

            client_id = MilvusHelper._generate_client_id(client_id, tenant_code, 32)
            secret_key = MilvusHelper._generate_secret_key(secret_key, 36)

            # HINT: Create user if not exists
            MilvusHelper._create_user_if_not_exists(client_id, secret_key)

            tenant_role_name: str = BaseMilvus._get_tenant_role_name_by_tenant_code(
                tenant_code
            )
            # HINT: Create role if not exists
            new = MilvusHelper._create_role_if_not_exists(tenant_role_name)
            if new:
                MilvusHelper._assign_role_to_user(
                    user_name=client_id, role_name=tenant_role_name
                )
            store_name: str = BaseMilvus._get_vector_store_name_by_tenant_code(
                tenant_code
            )

            MilvusHelper._create_vector_store_if_not_exists(
                store_name, db_name, vector_dimension, tenant_role_name
            )
            return MilvusDBInfo(
                tenant_db=db_name, client_id=client_id, secret_key=secret_key
            )

    @staticmethod
    def _generate_client_id(
        current_client_id: str, tenant_code: str, total_length: int
    ) -> str:
        """
        Returns a valid client_id. If current_client_id does not start with tenant_code-
        or its length does not match total_length, generate a new one with tenant_code- as prefix.
        """
        tenant_code = tenant_code.lower()
        prefix = f"{tenant_code}_"
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
    def _generate_secret_key(current_secret_key: str, size: int) -> str:
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
    def _create_vector_store_if_not_exists(
        store_name: str, db_name: str, vector_dimension: int, tenant_role_name: str
    ) -> None:
        """
        Creates a vector store (collection) if it does not exist, and assigns privileges.
        """
        # User admin client to create collection
        logger.debug(
            f"Creating vector store '{store_name}' and database '{db_name}' if they do not exist."
        )
        client = BaseMilvus.admin_client
        try:
            client.using_database(db_name)
            logger.debug(f"Using database '{db_name}' for vector store '{store_name}'.")
            if not client.has_collection(store_name):
                logger.debug(f"vector store '{store_name}' does not exist.")
                if vector_dimension is None or vector_dimension <= 0:
                    vector_dimension = MilvusHelper._milvus_dimension
                logger.debug(
                    f"Creating vector store '{store_name}' with dimension {vector_dimension}."
                )
                client.create_collection(
                    collection_name=store_name,
                    schema=BaseMilvus._get_vector_store_schema(
                        name=store_name, dimension=vector_dimension
                    ),
                )
                logger.info(f"Vector store '{store_name}' created successfully.")
                BaseMilvus._create_vector_store_index_if_not_exists(store_name)
                logger.debug(
                    f"Index for vector store '{store_name}' created successfully."
                )
                # HINT: Give tenant role privileges to the collection
                BaseMilvus._grant_tenant_privileges_to_collection_if_missing(
                    tenant_role_name, store_name
                )
                logger.debug(
                    f"Privileges for role '{tenant_role_name}' granted on collection '{store_name}'."
                )
                client.load_collection(store_name)
                logger.debug(f"collection '{store_name}' loaded.")
            else:
                client.load_collection(store_name)
                logger.debug(f"collection '{store_name}' loaded.")
        except Exception as ex:
            logger.error(f"Failed to create vector store '{store_name}': {ex}")
            raise Exception(f"Failed to create vector store '{store_name}': {ex}")

    @staticmethod
    def _get_or_add_current_volumes(
        tenant_id: str, user_id: str, password: str
    ) -> VectorStore:
        """
        Gets or creates a VectorStore instance for the given tenant/user.
        """
        return MilvusHelper._vector_stores.get_or_add(
            (tenant_id, user_id), lambda: VectorStore(tenant_id, user_id, password)
        )

    @staticmethod
    def get_tenant_client(
        tenant_client_id: str, tenant_client_secret: str, tenant_database: str
    ) -> MilvusClient:
        """
        Returns a MilvusClient for the given tenant credentials.
        """
        return MilvusClient(
            host=MilvusHelper._milvus_endpoint,
            port=MilvusHelper._milvus_port,
            user=tenant_client_id,
            password=tenant_client_secret,
            database=tenant_database,
        )

    @staticmethod
    def _create_database_if_not_exists(db_name: str) -> bool:
        """
        Checks if the database exists, creates it if not.
        """
        client = BaseMilvus.admin_client
        try:
            existing_dbs = client.list_databases()
            if db_name not in existing_dbs:
                client.create_database(db_name=db_name)
                logger.debug(f"Database '{db_name}' created successfully!")
            else:
                logger.debug(f"Database '{db_name}' already exists.")
            return True
        except Exception as ex:
            logger.error(f"cannot create database '{db_name}': {ex}")
            raise Exception(f"Failed to create database '{db_name}': {ex}")

    @staticmethod
    def _create_role_if_not_exists(role_name: str) -> bool:
        """
        Checks if the tenant role exists, creates it if not.
        """
        client = BaseMilvus.admin_client
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

    @staticmethod
    def _assign_role_to_user(user_name: str, role_name: str) -> None:
        """
        Assigns a role to a user if the assignment doesn't already exist.
        """
        client = BaseMilvus.admin_client
        try:
            # HINT: Check current roles of the user
            user_info = client.describe_user(user_name=user_name)
            logger.debug(f"user_info for '{user_name}': {user_info}")
            roles = user_info.get("roles", [])
            # If roles is a list of strings:
            if roles and isinstance(roles[0], str):
                current_roles = set(roles)
                logger.debug(
                    f"1 - Current roles for user '{user_name}': {current_roles}"
                )
            # If roles is a list of dicts:
            elif roles and isinstance(roles[0], dict):
                current_roles = {role.get("role_name", "") for role in roles}
                logger.debug(
                    f"2 - Current roles for user '{user_name}': {current_roles}"
                )
            else:
                current_roles = set()

            if role_name not in current_roles:
                client.grant_role(user_name=user_name, role_name=role_name)
                logger.debug(f"[✓] Assigned role '{role_name}' to user '{user_name}'.")
            else:
                logger.debug(f"[•] User '{user_name}' already has role '{role_name}'.")
        except Exception as e:
            logger.error(f"[!] Failed to assign role: {e}")
            raise Exception(
                f"Failed to assign role '{role_name}' to user '{user_name}': {e}"
            )

    @staticmethod
    def _create_user_if_not_exists(user_name: str, password: str) -> str:
        """
        Creates a user if it does not exist. Returns the password.
        """
        client = BaseMilvus.admin_client
        try:
            existing_users = client.list_users()
            if user_name not in existing_users:
                client.create_user(user_name=user_name, password=password)
                logger.debug(f"User '{user_name}' created successfully!")
            else:
                logger.debug(f"User '{user_name}' already exists.")
            return password
        except Exception as ex:
            logger.error(f"Failed to create user '{user_name}': {ex}")
            raise Exception(f"Failed to create user '{user_name}': {ex}")

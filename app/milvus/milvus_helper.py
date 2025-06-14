from threading import Lock
from typing import Any, List, Optional

from app.app_init import APP_SETTINGS
from app.logger import get_logger
from app.milvus.base_milvus import BaseMilvus
from app.milvus.vector_store import VectorStore
from app.models.embeded_vectors import EmbeddedVectors

# from app.models.milvus_db_info import MilvusDBInfo
from app.modules.concurrent_dict import ConcurrentDict

logger = get_logger("milvus_helper")


class MilvusHelper(BaseMilvus):
    __mhelper_init_lock: Lock = Lock()
    __mhelper_initialized: bool = False
    __vector_stores: ConcurrentDict = ConcurrentDict("_vector_stores")

    def __init__(self):
        logger.debug("Initializing MilvusHelper...")
        super().__init__()  # <-- This calls BaseMilvus.__init__()

    @staticmethod
    def initialize(**kwargs: Any) -> None:
        """
        Initializes the Milvus admin client and sets configuration.
        """
        with MilvusHelper.__mhelper_init_lock:
            if not MilvusHelper.__mhelper_initialized:
                try:
                    MilvusHelper()  # This will call __init__ and thus BaseMilvus.__init__()
                    BaseMilvus._set_admin_role_if_not_exists()
                    logger.debug("MilvusHelper initialized successfully.")
                except Exception as ex:
                    logger.error(f"Error initializing Milvus: {ex}")
                    raise ConnectionError(f"Error initializing Milvus: {ex}")
                MilvusHelper.__mhelper_initialized = True

    @staticmethod
    def insert_embedded_data(
        embedded_vector: List[EmbeddedVectors],
        tenant_code: str,
        token: str,
        **kwargs: Any,
    ) -> int:
        """
        Inserts embedded vectors into the tenant's vector store.
        """
        client_id, secret_key = MilvusHelper._split_token(token)
        valid_token = BaseMilvus._validate_token(token=token)
        if not valid_token:
            logger.error(f"Invalid token: {token}")
            raise ValueError("Invalid token.")

        tenant_store = MilvusHelper.__get_or_add_current_volumes(
            tenant_code, client_id, secret_key
        )
        logger.debug(
            f"Inserting {len(embedded_vector)} embedded vectors into vector store for tenant '{tenant_code}'."
        )
        tenant_store.insert_data(embedded_vector, **kwargs)
        return len(embedded_vector)

    @staticmethod
    def search_embedded_data(
        text_to_search: str, vector_to_search: List[float], parameters: dict
    ) -> Any:
        """
        Searches for embedded data in the tenant's vector store.
        """
        tenant_store = MilvusHelper.__get_or_add_current_volumes(
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
        tenant_store = MilvusHelper.__get_or_add_current_volumes(
            parameters["tenant_code"], parameters["client_id"], parameters["secret_key"]
        )
        return tenant_store.search_store(vector_to_search, parameters)

    @staticmethod
    def set_user(tenant_code: str, **kwargs: Any) -> dict:
        """
        Sets up a user for a tenant, creating all necessary resources if missing.
        Uses a lock to ensure thread safety.
        """

        return MilvusHelper._create_user_for_tenant(tenant_code=tenant_code, **kwargs)

    @staticmethod
    def _split_token(token: str) -> tuple[str, str]:
        """Splits a token into user_id and password."""
        try:
            user_id, password = token.split(":", 1)  # Split at the first colon
            return user_id, password
        except ValueError:
            raise ValueError("Invalid token format. Expected 'user_id:password'.")

    @staticmethod
    def set_vector_store(
        tenant_code: str, vector_dimension: int, token: str, **kwargs: Any
    ) -> dict:
        """
        Sets up a vector store for a tenant, creating all necessary resources if missing.
        Uses a lock to ensure thread safety.
        """
        client_id, secret_key = MilvusHelper._split_token(token)
        logger.debug(
            f"Setting up vector store for tenant '{tenant_code}' with client_id '{client_id}' and secret_key '{secret_key}'."
        )
        valid_token = BaseMilvus._validate_token(token=token)
        if not valid_token:
            logger.error(f"Invalid token: {token}")
            raise ValueError("Invalid token.")
        super_user = BaseMilvus._is_super_user(user_id=client_id)
        if not super_user:
            logger.error(f"User '{client_id}' is not a super user.")
            raise PermissionError("User is not a super user.")

        with MilvusHelper.__mhelper_init_lock:  # HINT: Lock to avoid race condition during vector store setup
            if not MilvusHelper.__mhelper_initialized:
                logger.error(
                    "MilvusHelper has not been initialized. Please call initialize() first."
                )
                raise Exception(
                    "Vector store has not been initialized properly. Please set required vector store values."
                )
            if not tenant_code:
                logger.error("tenant_code is required.")
                raise ValueError("tenant_code is required.")
            # HINT: Create user if not exists
            # BaseMilvus._create_user_if_not_exists(client_id, secret_key)

            # setup tenant store
            logger.debug(
                f"Setting up vector store for tenant '{tenant_code}' with client_id '{client_id}' and secret_key '{secret_key}'."
            )
            return BaseMilvus._setup_tenant_vector_store(
                tenant_code=tenant_code, vector_dimension=vector_dimension
            )

            # # HINT: Create database if not exists
            # db_name: str = MilvusHelper._get_db_name_by_tenant_code(tenant_code)
            # MilvusHelper.__create_database_if_not_exists(db_name)

            # client_id = MilvusHelper.__generate_client_id(client_id, tenant_code, 32)
            # secret_key = MilvusHelper.__generate_secret_key(secret_key, 36)

            # # HINT: Create user if not exists
            # MilvusHelper.__create_user_if_not_exists(client_id, secret_key)

            # tenant_role_name: str = BaseMilvus._get_tenant_role_name_by_tenant_code(
            #     tenant_code
            # )
            # # HINT: Create role if not exists
            # new = MilvusHelper._create_role_if_not_exists(tenant_role_name)
            # if new:
            #     MilvusHelper.__assign_role_to_user(
            #         user_name=client_id, role_name=tenant_role_name
            #     )
            # store_name: str = BaseMilvus._get_vector_store_name_by_tenant_code(
            #     tenant_code
            # )

            # MilvusHelper.__create_vector_store_if_not_exists(
            #     store_name, db_name, vector_dimension, tenant_role_name
            # )
            # return MilvusDBInfo(
            #    tenant_db=BaseMilvus._get_db_name_by_tenant_code(tenant_code), client_id=client_id, secret_key=secret_key
            # )

    # @staticmethod
    # def __create_vector_store_if_not_exists(
    #     store_name: str, db_name: str, vector_dimension: int, tenant_role_name: str
    # ) -> None:
    #     """
    #     Creates a vector store (collection) if it does not exist, and assigns privileges.
    #     """
    #     # User admin client to create collection
    #     logger.debug(
    #         f"Creating vector store '{store_name}' and database '{db_name}' if they do not exist."
    #     )
    #     client = MilvusHelper._get_helper_admin_client()
    #     try:
    #         client.using_database(db_name)
    #         logger.debug(f"Using database '{db_name}' for vector store '{store_name}'.")
    #         if not client.has_collection(store_name):
    #             logger.debug(f"vector store '{store_name}' does not exist.")
    #             if vector_dimension is None or vector_dimension <= 0:
    #                 vector_dimension = BaseMilvus._milvus_dimension
    #             logger.debug(
    #                 f"Creating vector store '{store_name}' with dimension {vector_dimension}."
    #             )
    #             client.create_collection(
    #                 collection_name=store_name,
    #                 schema=BaseMilvus._get_vector_store_schema(
    #                     name=store_name, dimension=vector_dimension
    #                 ),
    #             )
    #             logger.info(f"Vector store '{store_name}' created successfully.")
    #             BaseMilvus._create_vector_store_index_if_not_exists(store_name)
    #             logger.debug(
    #                 f"Index for vector store '{store_name}' created successfully."
    #             )
    #             # HINT: Give tenant role privileges to the collection
    #             BaseMilvus._grant_tenant_privileges_to_collection_if_missing(
    #                 tenant_role_name, store_name
    #             )
    #             logger.debug(
    #                 f"Privileges for role '{tenant_role_name}' granted on collection '{store_name}'."
    #             )
    #             client.load_collection(store_name)
    #             logger.debug(f"collection '{store_name}' loaded.")
    #         else:
    #             client.load_collection(store_name)
    #             logger.debug(f"collection '{store_name}' loaded.")
    #     except Exception as ex:
    #         logger.error(f"Failed to create vector store '{store_name}': {ex}")
    #         raise Exception(f"Failed to create vector store '{store_name}': {ex}")

    @staticmethod
    def __get_or_add_current_volumes(
        tenant_id: str, user_id: str, password: str
    ) -> VectorStore:
        """
        Gets or creates a VectorStore instance for the given tenant/user.
        """
        return MilvusHelper.__vector_stores.get_or_add(
            (tenant_id, user_id), lambda: VectorStore(tenant_id, user_id, password)
        )

    # @staticmethod
    # def __create_database_if_not_exists(db_name: str) -> bool:
    #     """
    #     Checks if the database exists, creates it if not.
    #     """
    #     client = MilvusHelper._get_helper_admin_client()
    #     try:
    #         existing_dbs = client.list_databases()
    #         if db_name not in existing_dbs:
    #             client.create_database(db_name=db_name)
    #             logger.debug(f"Database '{db_name}' created successfully!")
    #         else:
    #             logger.debug(f"Database '{db_name}' already exists.")
    #         return True
    #     except Exception as ex:
    #         logger.error(f"cannot create database '{db_name}': {ex}")
    #         raise Exception(f"Failed to create database '{db_name}': {ex}")

    # @staticmethod
    # def __assign_role_to_user(user_name: str, role_name: str) -> None:
    #     """
    #     Assigns a role to a user if the assignment doesn't already exist.
    #     """
    #     client = MilvusHelper._get_helper_admin_client()
    #     try:
    #         # HINT: Check current roles of the user
    #         user_info = client.describe_user(user_name=user_name)
    #         logger.debug(f"user_info for '{user_name}': {user_info}")
    #         roles = user_info.get("roles", [])
    #         # If roles is a list of strings:
    #         if roles and isinstance(roles[0], str):
    #             current_roles = set(roles)
    #             logger.debug(
    #                 f"1 - Current roles for user '{user_name}': {current_roles}"
    #             )
    #         # If roles is a list of dicts:
    #         elif roles and isinstance(roles[0], dict):
    #             current_roles = {role.get("role_name", "") for role in roles}
    #             logger.debug(
    #                 f"2 - Current roles for user '{user_name}': {current_roles}"
    #             )
    #         else:
    #             current_roles = set()

    #         if role_name not in current_roles:
    #             client.grant_role(user_name=user_name, role_name=role_name)
    #             logger.debug(f"[✓] Assigned role '{role_name}' to user '{user_name}'.")
    #         else:
    #             logger.debug(f"[•] User '{user_name}' already has role '{role_name}'.")
    #     except Exception as e:
    #         logger.error(f"[!] Failed to assign role: {e}")
    #         raise Exception(
    #             f"Failed to assign role '{role_name}' to user '{user_name}': {e}"
    #         )

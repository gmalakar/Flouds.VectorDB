# =============================================================================
# File: base_milvus.py
# Date: 2025-06-14
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import base64
import json
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
    utility,
)
from pymilvus.milvus_client.index import IndexParams

from app.app_init import APP_SETTINGS
from app.logger import get_logger
from app.models.reset_password_request import ResetPasswordRequest
from app.models.reset_password_response import ResetPasswordResponse
from app.modules.concurrent_dict import ConcurrentDict

logger = get_logger("BaseMilvus")


class BaseMilvus:
    """
    Base class for Milvus operations, including connection management,
    user/role/collection/index setup, and utility helpers.
    """

    __tenant_connections: ConcurrentDict = ConcurrentDict("_tenant_connections")
    __COLLECTION_SCHEMA_NAME: str = "vector_store_schema"
    __PRIMARY_FIELD_NAME: str = "flouds_vector_id"
    __VECTOR_FIELD_NAME: str = "flouds_vector"
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
    __admin_pwd_reset: bool = False
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

    @classmethod
    def initialize(cls) -> None:
        """
        Initializes the Milvus admin client and sets configuration.
        """
        with cls.__init_lock:
            if not cls.__initialized:
                # Read username from environment or settings
                username = (
                    os.getenv("VECTORDB_USERNAME") or APP_SETTINGS.vectordb.username
                )
                if not username or username.strip() == "":
                    raise ValueError(
                        "vectordb.username is missing! Set VECTORDB_USERNAME env or in your config."
                    )

                # Try to read password from plain text file
                password = None

                password_file = (
                    os.getenv("VECTORDB_PASSWORD_FILE")
                    or APP_SETTINGS.vectordb.password_file
                )

                if password_file and os.path.exists(password_file):
                    try:
                        logger.debug(
                            f"Attempting to read password from file: {password_file}"
                        )
                        with open(password_file, "r") as file:
                            password = file.read().strip()
                            if password:
                                logger.debug("Password successfully read from file")
                            else:
                                logger.warning(
                                    f"Password file {password_file} is empty"
                                )
                    except Exception as e:
                        logger.warning(
                            f"Failed to read password file {password_file}: {e}"
                        )

                # If no password from file, try environment variable or settings
                if not password:
                    password = (
                        os.getenv("VECTORDB_PASSWORD") or APP_SETTINGS.vectordb.password
                    )

                if not password or password.strip() == "":
                    raise ValueError(
                        "Milvus password is missing! Set VECTORDB_PASSWORD env var, provide a valid password file, or set it in your config."
                    )

                cls.__milvus_admin_username = username
                cls.__milvus_admin_password = password

                logger.info(f"Using Milvus username: {cls.__milvus_admin_username}")

                # Get endpoint from environment or settings
                endpoint = (
                    os.getenv("VECTORDB_ENDPOINT") or APP_SETTINGS.vectordb.endpoint
                )

                # Fix Docker hostname issues when running locally
                if endpoint == "milvus-standalone" and not os.getenv(
                    "VECTORDB_ENDPOINT"
                ):
                    # If running locally and using default Docker hostname, switch to localhost
                    endpoint = "localhost"
                    logger.info(
                        "Running locally: switched endpoint from 'milvus-standalone' to 'localhost'"
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
                        "vectordb.endpoint is invalid! Must be a valid URL or hostname."
                    )

                # Get port from environment or settings
                try:
                    port = int(os.getenv("VECTORDB_PORT") or APP_SETTINGS.vectordb.port)
                except Exception:
                    port = 19530

                if port and port > 0:
                    cls.__milvus_port = port
                    logger.debug(f"Using Milvus port: {cls.__milvus_port}")
                else:
                    logger.warning(
                        "vectordb.port is invalid! Using default port 19530."
                    )

                # Rest of the initialization...
                cls.__admin_role_name = APP_SETTINGS.vectordb.admin_role_name
                logger.info(f"Using Milvus admin role name: {cls.__admin_role_name}")
                milvus_url = cls._get_milvus_url()
                logger.info(f"Using Milvus endpoint: {milvus_url}")
                logger.info(f"Using Milvus port: {cls.__milvus_port}")
                logger.info(
                    f"Using Milvus admin username: {cls.__milvus_admin_username}"
                )

                # Create internal client properly
                cls.__minvus_admin_client = MilvusClient(
                    uri=milvus_url,
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

    @classmethod
    def _get_milvus_url(cls) -> str:
        """Gets the complete Milvus URL including port"""
        endpoint = cls.__milvus_endpoint
        # Remove trailing slash if present
        endpoint = endpoint.rstrip("/")
        # Don't add port if it's already in the URL
        if f":{cls.__milvus_port}" not in endpoint:
            return f"{endpoint}:{cls.__milvus_port}"
        return endpoint

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
        if not cls.__initialized or cls.__admin_pwd_reset:
            if (
                cls.__minvus_admin_client is None or cls.__admin_pwd_reset
            ):  # HINT: Check if the client is already initialized
                # create internal client
                cls.__minvus_admin_client = MilvusClient(
                    uri=cls._get_milvus_url(),
                    user=cls.__milvus_admin_username,
                    password=cls.__milvus_admin_password,
                )
            cls.__admin_pwd_reset = False
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
        try:
            alias = str(uuid.uuid4())  # Generate a unique alias
            connections.connect(
                uri=BaseMilvus._get_milvus_url(), token=token, alias=alias
            )
            logger.debug(f"Token validated successfully.")
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
    def _create_user_for_tenant(
        tenant_code: str, reset_user: bool, **kwargs: Any
    ) -> dict:
        """
        Creates a user for the tenant if it does not exist, or resets if requested.
        Returns a summary dict.
        Thread-safe for user creation.
        """
        summary = {
            "tenant_code": tenant_code,
            "client_id": None,
            "client_secret": None,
            "existing_user": False,
            "message": "",
        }
        admin_client = BaseMilvus.__get_internal_admin_client()
        current_user = BaseMilvus._get_current_user_of_a_tenant(tenant_code)

        if current_user:
            if reset_user:
                try:
                    admin_client.drop_user(user_name=current_user)
                    logger.debug(f"User '{current_user}' dropped successfully.")
                except MilvusException as e:
                    logger.error(f"Failed to drop user '{current_user}': {e}")
                    summary["message"] = f"Failed to drop user '{current_user}': {e}"
                    return summary
            else:
                summary.update(
                    {
                        "existing_user": True,
                        "client_id": current_user,
                        "message": f"User '{current_user}' already exists for tenant '{tenant_code}'.",
                    }
                )
                return summary

        # Create new user (thread-safe)
        with BaseMilvus.__user_create_lock:
            try:
                client_id = BaseMilvus.__generate_client_id("none", tenant_code)
                secret_key = BaseMilvus.__generate_secret_key("none")
                admin_client.create_user(user_name=client_id, password=secret_key)
                summary.update(
                    {
                        "existing_user": False,
                        "client_id": client_id,
                        "client_secret": secret_key,
                        "message": f"User created successfully.",
                    }
                )
                logger.debug(f"User created successfully!")
            except Exception as ex:
                logger.error(f"Failed to create user : {ex}")
                summary["message"] = f"Failed to create user : {ex}"
        return summary

    @staticmethod
    def __set_admin_password(new_password: str) -> None:
        """
        Updates the admin password in multiple storage locations:
        1. Password file (if configured and writable) as plain text
        2. Environment variable (as a temporary update)
        3. BaseMilvus.__milvus_admin_password class variable

        Args:
            new_password: The new admin password to store
        """
        # Try to write to password file if configured
        password_file = APP_SETTINGS.vectordb.password_file
        if password_file:
            try:
                # Ensure directory exists
                os.makedirs(os.path.dirname(password_file), exist_ok=True)

                # Write password as plain text to file
                with open(password_file, "w") as f:
                    f.write(new_password)

                logger.debug(
                    f"Admin password updated in password file: {password_file}"
                )
            except Exception as e:
                logger.warning(f"Failed to update password file {password_file}: {e}")

        # Try to update environment variable
        try:
            os.environ["VECTORDB_PASSWORD"] = new_password
            logger.debug("Admin password updated in environment variable")
        except Exception as e:
            logger.warning(
                f"Failed to update VECTORDB_PASSWORD environment variable: {e}"
            )

        # Always update the class variable
        BaseMilvus.__milvus_admin_password = new_password
        BaseMilvus.__admin_pwd_reset = True
        logger.debug("Admin password updated in memory")

    @staticmethod
    def _reset_admin_user_password(
        request: ResetPasswordRequest, **kwargs: Any
    ) -> ResetPasswordResponse:
        """
        Resets the password for a user in the system.
        Thread-safe implementation for password management.
        Enforces password policy for security.

        Args:
            request: The password reset request containing user details
            **kwargs: Additional parameters

        Returns:
            ResetPasswordResponse with operation results
        """
        response: ResetPasswordResponse = ResetPasswordResponse(
            user_name=request.user_name,
            root_user=False,
            success=False,
            message="",
            reset_flag=False,
        )

        # Check password policy
        password = request.new_password
        policy_errors = []

        # Define password requirements with clearer, non-repetitive messages
        requirements = [
            (len(password) >= 8, "at least 8 characters"),
            (bool(re.search(r"[A-Z]", password)), "one uppercase letter"),
            (bool(re.search(r"[a-z]", password)), "one lowercase letter"),
            (bool(re.search(r"[0-9]", password)), "one digit"),
            (
                bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password)),
                'one special character (!@#$%^&*(),.?":{}|<>)',
            ),
        ]

        # Build the list of failed requirements
        for requirement_met, requirement_desc in requirements:
            if not requirement_met:
                policy_errors.append(requirement_desc)

        # If password policy fails, return error with a cleaner message
        if policy_errors:
            response.message = f"Password policy violation - Your password must include: {', '.join(policy_errors)}."
            return response

        admin_client = BaseMilvus.__get_internal_admin_client()
        # Use a lock to ensure thread safety
        lock = BaseMilvus.__user_create_lock
        with lock:
            try:
                admin_user = (
                    request.user_name.lower()
                    == BaseMilvus.__milvus_admin_username.lower()
                )
                if admin_user:
                    response.root_user = True
                    if request.old_password != BaseMilvus.__milvus_admin_password:
                        response.message = "Authentication failed: The provided password does not match the current admin password. Password reset requires correct authentication."
                        return response
                    admin_client.update_password(
                        user_name=request.user_name,
                        old_password=request.old_password,
                        new_password=request.new_password,
                    )
                    BaseMilvus.__set_admin_password(request.new_password)
                    response.success = True
                    response.reset_flag = True
                    response.message = "Password successfully reset for the admin user."
                    logger.debug("Admin password reset completed successfully.")
                else:
                    response.message = f"Operation not permitted: '{request.user_name}' is not an admin user."
            except Exception as ex:
                logger.error(
                    f"Password reset operation failed for user '{request.user_name}': {ex}"
                )
                response.message = (
                    f"Password reset failed for user '{request.user_name}': {str(ex)}"
                )
        return response

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
        return ["chunk", "meta", "model"]

    @staticmethod
    def _get_primary_key_name() -> str:
        """
        Returns the primary key name from settings or the default.
        """
        return APP_SETTINGS.vectordb.primary_key or BaseMilvus.__PRIMARY_FIELD_NAME

    @staticmethod
    def _get_vector_field_name() -> str:
        """
        Returns the vector field name from settings or the default.
        """
        return APP_SETTINGS.vectordb.vector_field_name or BaseMilvus.__VECTOR_FIELD_NAME

    @staticmethod
    def _get_primary_key_type() -> str:
        """
        Returns the primary key type from settings or 'VARCHAR' as default.
        """
        return (APP_SETTINGS.vectordb.primary_key_data_type or "VARCHAR").upper()

    @staticmethod
    def _get_dtype_map() -> dict:
        """
        Returns a mapping from string type names to Milvus DataType.
        """
        return {
            "VARCHAR": DataType.VARCHAR,
            "INT64": DataType.INT64,
            "INT": DataType.INT64,
            "STRING": DataType.VARCHAR,
        }

    @staticmethod
    def _get_vector_store_schema(name: str, dimension: int = 256) -> CollectionSchema:
        """
        Returns the collection schema for a vector store.
        Uses custom primary key and type from settings.
        Uses custom vector field name from settings.
        """
        primary_key = BaseMilvus._get_primary_key_name()
        primary_key_type = BaseMilvus._get_primary_key_type()
        vector_field_name = BaseMilvus._get_vector_field_name()

        dtype_map = BaseMilvus._get_dtype_map()
        dtype = dtype_map.get(primary_key_type, DataType.VARCHAR)
        auto_id = dtype == DataType.INT64

        pk_field_kwargs = {
            "name": primary_key,
            "dtype": dtype,
            "is_primary": True,
            "auto_id": auto_id,
            "description": f"Primary key ({primary_key_type})",
        }
        if dtype == DataType.VARCHAR:
            pk_field_kwargs["max_length"] = 256

        fields = [
            FieldSchema(**pk_field_kwargs),
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
                enable_match=True,
                enable_analyzer=True,
                description="Model used for embedding (e.g., 'openai', 'cohere', etc.)",
            ),
            FieldSchema(
                name=vector_field_name,
                dtype=DataType.FLOAT_VECTOR,
                dim=dimension,
                description="Vector of the chunk",
            ),
            FieldSchema(
                name="meta",
                dtype=DataType.VARCHAR,
                max_length=4096,
                description="Extra metadata as JSON string",
            ),
        ]
        return CollectionSchema(
            name=name,
            fields=fields,
            description="A collection for storing vectors of a document along with document's meta data",
            enable_dynamic_field=True,
        )

    @staticmethod
    def _create_vector_store_index_if_not_exists(
        collection_name: str, tenant_code: str
    ) -> bool:
        """
        Creates the index for the given collection in the tenant's database if it does not exist.
        Returns True if created, False if already exists.
        Raises Exception on error.
        """
        vector_index_name = "flouds_vector_index"
        model_index_name = "flouds_model_index"
        vector_field_name = BaseMilvus._get_vector_field_name()
        nlist = APP_SETTINGS.vectordb.index_params.nlist or 1024
        metric_type = APP_SETTINGS.vectordb.index_params.metric_type or "COSINE"
        index_type = APP_SETTINGS.vectordb.index_params.index_type or "IVF_FLAT"
        try:
            with BaseMilvus.__db_switch_lock:
                db_admin_client = BaseMilvus._get_or_create_tenant_connection(
                    tenant_code
                )
                vector_index_params = {
                    "field_name": vector_field_name,
                    "index_type": index_type,
                    "metric_type": metric_type,
                    "params": {"nlist": nlist},
                    "index_name": vector_index_name,
                }
                # Check if index exists
                indexes = db_admin_client.list_indexes(collection_name=collection_name)
                existing = set()
                for idx in indexes:
                    if isinstance(idx, dict) and "index_name" in idx:
                        existing.add(idx["index_name"])
                    elif isinstance(idx, str):
                        existing.add(idx)

                if vector_index_name not in existing:
                    ip = IndexParams()
                    ip.add_index(
                        field_name=vector_index_params["field_name"],
                        index_type=vector_index_params["index_type"],
                        index_name=vector_index_params["index_name"],
                        metric_type=vector_index_params["metric_type"],
                        params=vector_index_params["params"],
                    )
                    db_admin_client.create_index(
                        collection_name=collection_name, index_params=ip
                    )
                    logger.debug(
                        f"Index '{vector_index_name}' created on 'vector' in '{collection_name}'."
                    )
                    created = True
                else:
                    logger.debug(
                        f"Index '{vector_index_name}' already exists on '{collection_name}'."
                    )
                    created = False
                # Create model index if it does not exist
                if model_index_name not in existing:
                    ip = IndexParams()
                    ip.add_index(
                        field_name="model",
                        index_type="INVERTED",
                        index_name=model_index_name,
                    )
                    db_admin_client.create_index(
                        collection_name=collection_name, index_params=ip
                    )
                    logger.debug(
                        f"Index '{model_index_name}' created on 'model' in '{collection_name}'."
                    )
                    created = True
                else:
                    logger.debug(
                        f"Index '{model_index_name}' already exists on '{collection_name}'."
                    )
                    created = False

            return created

        except Exception as e:
            logger.error(
                f"Cannot create index '{vector_index_name}' for tenant '{tenant_code}': {e}"
            )
            raise Exception(
                f"Failed to create index '{vector_index_name}' for tenant '{tenant_code}': {e}"
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
                    admin_client.drop_user(user_name=current_user)
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

                # 2. Role
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

                # 3. Privileges

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

                # 4. Assign role to user
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

            # 5. Index
            # Create index if it does not exist
            created = BaseMilvus._create_vector_store_index_if_not_exists(
                collection_name=collection_name, tenant_code=tenant_code
            )
            if created:
                summary["index_created"] = True
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

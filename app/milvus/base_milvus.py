# =============================================================================
# File: base_milvus.py
# Description: Base class for Milvus operations with connection management and utilities
# Author: Goutam Malakar
# Date: 2025-01-15
# Version: 1.0.0
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import os
import random
import re
import string
from base64 import urlsafe_b64encode
from os import environ, getenv, urandom
from threading import Lock
from typing import Any, List, Optional
from uuid import uuid4

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
from app.exceptions.custom_exceptions import (
    CollectionError,
    ConfigurationError,
    MilvusConnectionError,
    MilvusOperationError,
    TenantError,
    UserManagementError,
    VectorStoreError,
)
from app.logger import get_logger
from app.milvus.connection_pool import milvus_pool
from app.models.reset_password_request import ResetPasswordRequest
from app.models.reset_password_response import ResetPasswordResponse
from app.modules.concurrent_dict import ConcurrentDict
from app.utils.input_validator import (
    validate_file_path,
    validate_tenant_code,
)
from app.utils.log_sanitizer import sanitize_for_log

logger = get_logger("BaseMilvus")


class BaseMilvus:
    """
    Base class for Milvus operations with comprehensive database management.

    Provides connection management, user/role administration, collection/index
    setup, and utility functions for multi-tenant vector database operations.
    All operations are thread-safe and support connection pooling.
    """

    __tenant_connections: ConcurrentDict = ConcurrentDict("_tenant_connections")
    __COLLECTION_SCHEMA_NAME: str = "vector_store_schema"
    __PRIMARY_FIELD_NAME: str = "flouds_vector_id"
    __VECTOR_FIELD_NAME: str = "flouds_vector"
    __DB_NAME_SUFFIX: str = "_vectorstore"
    __TENANT_NAME_SUFFIX: str = "_tenant_role"
    __SPARSE_INDEX_NAME: str = "flouds_sparse_vector_index"
    __VECTOR_INDEX_NAME: str = "flouds_vector_index"
    __CLIENT_ID_LENGTH: int = 32
    __CLIENT_SECRET_LENGTH: int = 36
    __TENANT_ROLE_PRIVILEGES: List[str] = [
        "CreateIndex",
        "Search",
        "Insert",
        "Upsert",
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
                cls._load_credentials()
                cls._configure_endpoint()
                cls._configure_port()
                cls._setup_admin_client()
                cls.__initialized = True

    @classmethod
    def _load_credentials(cls) -> None:
        """
        Load Milvus admin credentials from environment variables or configuration.

        Raises:
            ConfigurationError: If username or password is missing or invalid
        """
        username = getenv("VECTORDB_USERNAME") or APP_SETTINGS.vectordb.username
        if not username or username.strip() == "":
            raise ConfigurationError(
                "vectordb.username is missing! Set VECTORDB_USERNAME env or in your config."
            )

        password = cls._load_password()
        if not password or password.strip() == "":
            raise ConfigurationError(
                "Milvus password is missing! Set VECTORDB_PASSWORD env var, provide a valid password file, or set it in your config."
            )

        cls.__milvus_admin_username = username
        cls.__milvus_admin_password = password
        logger.info(
            f"Using Milvus username: {sanitize_for_log(cls.__milvus_admin_username)}"
        )

    @classmethod
    def _load_password(cls) -> Optional[str]:
        """
        Load password from file or environment variable.

        Returns:
            Optional[str]: Password if found, None otherwise
        """
        password_file = (
            getenv("VECTORDB_PASSWORD_FILE") or APP_SETTINGS.vectordb.password_file
        )

        if password_file:
            password = cls._read_password_file(password_file)
            if password:
                return password

        return getenv("VECTORDB_PASSWORD") or APP_SETTINGS.vectordb.password

    @classmethod
    def _read_password_file(cls, password_file: str) -> Optional[str]:
        """
        Safely read password from specified file with path validation.

        Args:
            password_file (str): Path to password file

        Returns:
            Optional[str]: Password content if file exists and readable, None otherwise
        """
        try:
            safe_password_file = validate_file_path(password_file)
            if os.path.exists(safe_password_file):
                logger.debug(
                    f"Attempting to read password from file: {safe_password_file}"
                )
                with open(safe_password_file, "r") as file:
                    password = file.read().strip()
                if password:
                    logger.debug("Password successfully read from file")
                    return password
                else:
                    logger.warning(f"Password file {password_file} is empty")
        except Exception as e:
            logger.warning(f"Failed to read password file {password_file}: {e}")
        return None

    @classmethod
    def _configure_endpoint(cls) -> None:
        """Configure Milvus endpoint from environment or settings."""
        endpoint = getenv("VECTORDB_ENDPOINT") or APP_SETTINGS.vectordb.endpoint

        # Add protocol if missing
        if not re.match(r"^https?://", endpoint):
            endpoint = f"http://{endpoint}"

        if (
            endpoint
            and isinstance(endpoint, str)
            and re.match(r"^https?://|^[\w\.-]+$", endpoint)
        ):
            cls.__milvus_endpoint = endpoint
        else:
            raise ConfigurationError(
                "vectordb.endpoint is invalid! Must be a valid URL or hostname."
            )

    @classmethod
    def _configure_port(cls) -> None:
        """Configure Milvus port from environment or settings."""
        try:
            port = int(getenv("VECTORDB_PORT") or APP_SETTINGS.vectordb.port)
        except Exception:
            port = 19530

        if port and port > 0:
            cls.__milvus_port = port
            logger.debug(f"Using Milvus port: {cls.__milvus_port}")
        else:
            logger.warning("vectordb.port is invalid! Using default port 19530.")

    @classmethod
    def _setup_admin_client(cls) -> None:
        """Setup and verify admin client connection."""
        cls.__admin_role_name = APP_SETTINGS.vectordb.admin_role_name
        milvus_url = cls._get_milvus_url()

        logger.info(f"Using Milvus admin role name: {cls.__admin_role_name}")
        logger.info(f"Using Milvus endpoint: {milvus_url}")
        logger.info(f"Using Milvus port: {cls.__milvus_port}")
        logger.info(f"Using Milvus admin username: {cls.__milvus_admin_username}")

        cls.__minvus_admin_client = MilvusClient(
            uri=milvus_url,
            user=cls.__milvus_admin_username,
            password=cls.__milvus_admin_password,
        )

        cls._verify_connection()

    @classmethod
    def _verify_connection(cls) -> None:
        """Verify Milvus connection is working."""
        try:
            if not cls.check_connection(cls.__minvus_admin_client):
                logger.error("Milvus connection failed!")
                raise MilvusConnectionError(
                    "Failed to connect to Milvus. Please check your configuration."
                )
        except (ConnectionError, TimeoutError) as ex:
            logger.error(f"Failed to connect to Milvus: {ex}")
            raise MilvusConnectionError(f"Failed to connect to Milvus: {ex}")
        except Exception as ex:
            logger.error(f"Unexpected error connecting to Milvus: {ex}")
            raise MilvusConnectionError(f"Failed to connect to Milvus: {ex}")

    @classmethod
    def _get_milvus_url(cls) -> str:
        """Gets the complete Milvus URL including port"""
        endpoint = cls.__milvus_endpoint.rstrip("/")
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
            logger.debug(f"user_info for '{sanitize_for_log(user_name)}': {user_info}")
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
                logger.debug(
                    f"Assigned role '{sanitize_for_log(role_name)}' to user '{sanitize_for_log(user_name)}'."
                )
            else:
                logger.debug(
                    f"User '{sanitize_for_log(user_name)}' already has role '{sanitize_for_log(role_name)}'."
                )
        except MilvusException as e:
            logger.error(f"Milvus error assigning role: {e}")
            raise UserManagementError(
                f"Failed to assign role '{role_name}' to user '{user_name}': {e}"
            )
        except Exception as e:
            logger.error(f"Unexpected error assigning role: {e}")
            raise UserManagementError(
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
                    user_name=APP_SETTINGS.vectordb.username,
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

        except MilvusException as ex:
            logger.error(f"Milvus error setting up admin role: {ex}")
            raise MilvusOperationError(f"Error setting up Milvus admin role: {ex}")
        except Exception as ex:
            logger.error(f"Unexpected error setting up admin role: {ex}")
            raise MilvusOperationError(f"Error setting up Milvus admin role: {ex}")

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
                logger.debug(
                    f"Role '{sanitize_for_log(role_name)}' created successfully!"
                )
                return True
            else:
                logger.debug(f"Role '{sanitize_for_log(role_name)}' already exists.")
            return False
        except MilvusException as ex:
            logger.error(f"Milvus error creating role '{role_name}': {ex}")
            raise UserManagementError(f"Failed to create role '{role_name}': {ex}")
        except Exception as ex:
            logger.error(f"Unexpected error creating role '{role_name}': {ex}")
            raise UserManagementError(f"Failed to create role '{role_name}': {ex}")

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
        Generate role name for a tenant using standardized naming convention.

        Args:
            tenant_code (str): Tenant identifier code

        Returns:
            str: Formatted role name with tenant suffix
        """
        validated_code = validate_tenant_code(tenant_code)
        return f"{validated_code}{BaseMilvus.__TENANT_NAME_SUFFIX}"

    @staticmethod
    def _get_db_name_by_tenant_code(tenant_code: str) -> str:
        """
        Generate database name for a tenant using standardized naming convention.

        Args:
            tenant_code (str): Tenant identifier code

        Returns:
            str: Formatted database name with vectorstore suffix
        """
        validated_code = validate_tenant_code(tenant_code)
        return f"{validated_code}{BaseMilvus.__DB_NAME_SUFFIX}"

    @staticmethod
    def _get_vector_store_name_by_tenant_code(tenant_code: str) -> str:
        """
        Returns the vector store (collection) name for a given tenant code.
        """
        validated_code = validate_tenant_code(tenant_code)
        return f"{BaseMilvus.__COLLECTION_SCHEMA_NAME}_for_{validated_code}".lower()

    @staticmethod
    def _get_vector_store_name_by_tenant_code_modelname(
        tenant_code: str, model_name: str
    ) -> str:
        """
        Returns the vector store (collection) name for a given tenant code and model name.
        """
        validated_code = validate_tenant_code(tenant_code)
        # Sanitize model_name to ensure it's safe for collection naming
        safe_model_name = model_name.lower().replace("-", "_").replace(".", "_")
        return f"{BaseMilvus.__COLLECTION_SCHEMA_NAME}_for_{validated_code}_{safe_model_name}".lower()

    @staticmethod
    def _check_database_exists(tenant_code: str) -> bool:
        """
        Checks if the database for the given tenant exists.
        """
        try:
            db_name = BaseMilvus._get_db_name_by_tenant_code(tenant_code)
            admin_client = BaseMilvus.__get_internal_admin_client()
            db_list = admin_client.list_databases()
            return db_name in db_list
        except Exception as ex:
            logger.error(
                f"Error checking database existence for tenant '{sanitize_for_log(tenant_code)}': {ex}"
            )
            return False

    @staticmethod
    def _check_collection_exists(tenant_code: str, model_name: str) -> bool:
        """
        Checks if the collection for the given tenant and model exists.
        """
        try:
            if not BaseMilvus._check_database_exists(tenant_code):
                return False

            collection_name = (
                BaseMilvus._get_vector_store_name_by_tenant_code_modelname(
                    tenant_code, model_name
                )
            )

            with BaseMilvus.__db_switch_lock:
                db_admin_client = BaseMilvus._get_or_create_tenant_connection(
                    tenant_code
                )
                collections = db_admin_client.list_collections()
                return collection_name in collections
        except Exception as ex:
            logger.error(
                f"Error checking collection existence for tenant '{sanitize_for_log(tenant_code)}' and model '{sanitize_for_log(model_name)}': {ex}"
            )
            return False

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
        expected_length = len(urlsafe_b64encode(urandom(size)).decode("utf-8"))

        def is_urlsafe_base64(s: str) -> bool:
            return re.fullmatch(r"^[A-Za-z0-9_\-]+={0,2}$", s) is not None

        if (
            not current_secret_key
            or len(current_secret_key) != expected_length
            or not is_urlsafe_base64(current_secret_key)
        ):
            return urlsafe_b64encode(os.urandom(size)).decode("utf-8")
        return current_secret_key

    @staticmethod
    def _validate_token(token: str) -> bool:
        """
        Validates a Milvus token by attempting a connection.
        Returns True if valid, False otherwise.
        """
        try:
            # Remove 'Bearer ' prefix if present
            if token.startswith("Bearer "):
                token = token[7:].strip()
            alias = str(uuid4())  # Generate a unique alias
            uri = BaseMilvus._get_milvus_url()
            # Do not log token for security reasons
            connections.connect(uri=uri, token=token, alias=alias)
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
                logger.error(f"Failed to create user: {ex}")
                summary["message"] = f"Failed to create user: {ex}"
        return summary

    @staticmethod
    def __set_admin_password(new_password: str) -> None:
        """
        Update the admin password in all storage locations.

        Args:
            new_password (str): The new admin password to store.

        Returns:
            None
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
            environ["VECTORDB_PASSWORD"] = new_password
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
        Reset the password for a user in the system.

        Args:
            request (ResetPasswordRequest): The password reset request object.
            **kwargs: Additional keyword arguments.

        Returns:
            ResetPasswordResponse: The response object indicating the result.
        """
        response = ResetPasswordResponse(
            user_name=request.user_name,
            root_user=False,
            success=False,
            message="",
            reset_flag=False,
        )

        # Validate password policy
        policy_error = BaseMilvus._validate_password_policy(request.new_password)
        if policy_error:
            response.message = policy_error
            return response

        # Perform password reset
        with BaseMilvus.__user_create_lock:
            return BaseMilvus._perform_password_reset(request, response)

    @staticmethod
    def _validate_password_policy(password: str) -> Optional[str]:
        """
        Validate password against policy requirements.

        Args:
            password (str): The password to validate.

        Returns:
            Optional[str]: None if valid, otherwise a string describing the policy violation.
        """
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

        policy_errors = [desc for met, desc in requirements if not met]
        if policy_errors:
            from html import escape

            sanitized_errors = [
                escape(sanitize_for_log(error)) for error in policy_errors
            ]
            return f"Password policy violation - Your password must include: {', '.join(sanitized_errors)}."
        return None

    @staticmethod
    def _perform_password_reset(
        request: ResetPasswordRequest, response: ResetPasswordResponse
    ) -> ResetPasswordResponse:
        """
        Perform the actual password reset operation.

        Args:
            request (ResetPasswordRequest): The password reset request object.
            response (ResetPasswordResponse): The response object to update.

        Returns:
            ResetPasswordResponse: The updated response object.
        """
        admin_client = BaseMilvus.__get_internal_admin_client()

        try:
            admin_user = (
                request.user_name.lower() == BaseMilvus.__milvus_admin_username.lower()
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
                response.message = f"Operation not permitted: '{sanitize_for_log(request.user_name)}' is not an admin user."
        except MilvusException as ex:
            logger.error(
                f"Milvus error during password reset for user '{sanitize_for_log(request.user_name)}': {ex}"
            )
            response.message = f"Database error during password reset for user '{sanitize_for_log(request.user_name)}': {str(ex)}"
        except Exception as ex:
            logger.error(
                f"Unexpected error during password reset for user '{sanitize_for_log(request.user_name)}': {ex}"
            )
            response.message = f"Password reset failed for user '{sanitize_for_log(request.user_name)}': {str(ex)}"
        return response

    @staticmethod
    def _get_tenant_client(
        tenant_client_id: str, tenant_client_secret: str, tenant_database: str
    ) -> MilvusClient:
        """
        Get a pooled MilvusClient for the given tenant credentials.

        Args:
            tenant_client_id (str): The tenant's client ID.
            tenant_client_secret (str): The tenant's client secret.
            tenant_database (str): The tenant's database name.

        Returns:
            MilvusClient: The pooled client instance.
        """
        logger.debug(
            f"Getting pooled connection for tenant: {sanitize_for_log(tenant_client_id)}, database: {sanitize_for_log(tenant_database)}"
        )
        return milvus_pool.get_connection(
            uri=BaseMilvus._get_milvus_url(),
            user=tenant_client_id,
            password=tenant_client_secret,
            database=tenant_database,
        )

    @staticmethod
    def get_chunk_meta_output_fields() -> list[str]:
        """
        Get the output fields for chunk and meta.

        Returns:
            list[str]: List of output field names.
        """
        return ["chunk", "meta", "model"]

    @staticmethod
    def _get_primary_key_name() -> str:
        """
        Get the primary key name from settings or the default.

        Returns:
            str: The primary key field name.
        """
        return (
            getattr(APP_SETTINGS.vectordb, "primary_key", None)
            or BaseMilvus.__PRIMARY_FIELD_NAME
        )

    @staticmethod
    def _get_vector_field_name() -> str:
        """
        Get the vector field name from settings or the default.

        Returns:
            str: The vector field name.
        """
        return (
            getattr(APP_SETTINGS.vectordb, "vector_field_name", None)
            or BaseMilvus.__VECTOR_FIELD_NAME
        )

    @staticmethod
    def _get_primary_key_type() -> str:
        """
        Get the primary key type from settings or 'VARCHAR' as default.

        Returns:
            str: The primary key type (e.g., 'VARCHAR', 'INT64').
        """
        return (
            getattr(APP_SETTINGS.vectordb, "primary_key_data_type", None) or "VARCHAR"
        ).upper()

    @staticmethod
    def _get_dtype_map() -> dict[str, Any]:
        """
        Get a mapping from string type names to Milvus DataType.

        Returns:
            dict[str, Any]: Mapping from type name to DataType.
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
        Get the collection schema for a vector store.

        Args:
            name (str): The name of the collection.
            dimension (int, optional): The vector dimension. Defaults to 256.

        Returns:
            CollectionSchema: The schema object for the collection.
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
        ]

        # Add sparse vector field only if SPARSE_FLOAT_VECTOR is available in this pymilvus version
        if hasattr(DataType, "SPARSE_FLOAT_VECTOR"):
            fields.append(
                FieldSchema(
                    name="sparse_vector",
                    dtype=DataType.SPARSE_FLOAT_VECTOR,
                    description="Sparse vector representation of the chunk",
                )
            )

        fields.append(
            FieldSchema(
                name="meta",
                dtype=DataType.VARCHAR,
                max_length=4096,
                description="Extra metadata as JSON string",
            )
        )

        return CollectionSchema(
            name=name,
            fields=fields,
            description="A collection for storing vectors of a document along with document's meta data",
            enable_dynamic_field=True,
        )

    @staticmethod
    def _get_custom_vector_store_schema(
        name: str, dimension: int, metadata_length: int = 4096
    ) -> CollectionSchema:
        """
        Get a custom collection schema for a vector store with specified parameters.

        Args:
            name (str): The name of the collection.
            dimension (int): The vector dimension.
            metadata_length (int, optional): The max length for metadata. Defaults to 4096.

        Returns:
            CollectionSchema: The schema object for the collection.
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
                name=vector_field_name,
                dtype=DataType.FLOAT_VECTOR,
                dim=dimension,
                description="Vector of the chunk",
            ),
        ]

        # Add sparse vector field only if SPARSE_FLOAT_VECTOR is available in this pymilvus version
        if hasattr(DataType, "SPARSE_FLOAT_VECTOR"):
            fields.append(
                FieldSchema(
                    name="sparse_vector",
                    dtype=DataType.SPARSE_FLOAT_VECTOR,
                    description="Sparse vector representation of the chunk",
                )
            )

        fields.append(
            FieldSchema(
                name="meta",
                dtype=DataType.VARCHAR,
                max_length=metadata_length,
                description="Extra metadata as JSON string",
            )
        )

        return CollectionSchema(
            name=name,
            fields=fields,
            description="A collection for storing vectors of a document along with document's meta data",
            enable_dynamic_field=True,
        )

    @staticmethod
    def _generate_custom_schema(
        tenant_code: str,
        model_name: str,
        dimension: int,
        nlist: int = 1024,
        metric_type: str = "COSINE",
        index_type: str = "IVF_FLAT",
        metadata_length: int = 4096,
        drop_ratio_build: float = 0.1,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Generate a custom schema with specified parameters for a tenant and model.

        Args:
            tenant_code (str): The tenant code.
            model_name (str): The model name.
            dimension (int): The vector dimension.
            nlist (int, optional): Number of clusters for IVF index. Defaults to 1024.
            metric_type (str, optional): Metric type for index. Defaults to "COSINE".
            index_type (str, optional): Index type. Defaults to "IVF_FLAT".
            metadata_length (int, optional): Metadata max length. Defaults to 4096.
            drop_ratio_build (float, optional): Drop ratio for sparse index. Defaults to 0.1.
            **kwargs: Additional keyword arguments.

        Returns:
            dict[str, Any]: Summary of schema generation.
        """
        summary = BaseMilvus._init_schema_summary(
            tenant_code,
            model_name,
            dimension,
            nlist,
            metric_type,
            index_type,
            metadata_length,
            drop_ratio_build,
        )

        try:
            db_name, collection_name = BaseMilvus._prepare_schema_names(
                tenant_code, model_name, summary
            )
            BaseMilvus._ensure_database_exists(db_name, tenant_code)
            BaseMilvus._create_collection_with_schema(
                tenant_code, collection_name, dimension, metadata_length, summary
            )
            BaseMilvus._create_custom_indexes(
                tenant_code,
                collection_name,
                index_type,
                metric_type,
                nlist,
                drop_ratio_build,
                summary,
            )
            BaseMilvus._grant_collection_permissions(tenant_code, collection_name)
            return summary
        except Exception as ex:
            logger.error(f"Error generating custom schema: {ex}")
            summary["message"] = f"Failed to generate custom schema: {ex}"
            raise VectorStoreError(f"Failed to generate custom schema: {ex}")

    @staticmethod
    def _init_schema_summary(
        tenant_code: str,
        model_name: str,
        dimension: int,
        nlist: int,
        metric_type: str,
        index_type: str,
        metadata_length: int,
        drop_ratio_build: float,
    ) -> dict[str, Any]:
        """Initialize schema generation summary."""
        return {
            "tenant_code": tenant_code,
            "model_name": model_name,
            "collection_name": None,
            "db_name": None,
            "schema_created": False,
            "schema_exists": False,
            "vector_index": "not created",
            "index_name": BaseMilvus.__VECTOR_INDEX_NAME,
            "sparse_index": "not created",
            "sparse_index_name": BaseMilvus.__SPARSE_INDEX_NAME,
            "dimension": dimension,
            "nlist": nlist,
            "metric_type": metric_type,
            "index_type": index_type,
            "metadata_length": metadata_length,
            "drop_ratio_build": drop_ratio_build,
            "message": "Custom schema generation completed successfully.",
        }

    @staticmethod
    def _prepare_schema_names(
        tenant_code: str, model_name: str, summary: dict
    ) -> tuple[str, str]:
        """Prepare database and collection names for schema generation."""
        db_name = BaseMilvus._get_db_name_by_tenant_code(tenant_code)
        collection_name = BaseMilvus._get_vector_store_name_by_tenant_code_modelname(
            tenant_code, model_name
        )
        summary["db_name"] = db_name
        summary["collection_name"] = collection_name
        return db_name, collection_name

    @staticmethod
    def _ensure_database_exists(db_name: str, tenant_code: str) -> None:
        """Ensure database exists for tenant."""
        admin_client = BaseMilvus.__get_internal_admin_client()
        db_list = admin_client.list_databases()
        if db_name not in db_list:
            admin_client.create_database(db_name)
            logger.info(f"Database '{db_name}' created for tenant '{tenant_code}'.")

    @staticmethod
    def _create_collection_with_schema(
        tenant_code: str,
        collection_name: str,
        dimension: int,
        metadata_length: int,
        summary: dict,
    ) -> None:
        """Create collection with custom schema if it doesn't exist."""
        with BaseMilvus.__db_switch_lock:
            db_admin_client = BaseMilvus._get_or_create_tenant_connection(tenant_code)
            collections = db_admin_client.list_collections()

            if collection_name not in collections:
                db_admin_client.create_collection(
                    collection_name=collection_name,
                    schema=BaseMilvus._get_custom_vector_store_schema(
                        collection_name, dimension, metadata_length
                    ),
                )
                logger.info(
                    f"Collection '{collection_name}' created with custom schema."
                )
                summary["schema_created"] = True
            else:
                summary["schema_exists"] = True
                logger.info(f"Collection '{collection_name}' already exists.")

    @staticmethod
    def _create_custom_indexes(
        tenant_code: str,
        collection_name: str,
        index_type: str,
        metric_type: str,
        nlist: int,
        drop_ratio_build: float,
        summary: dict,
    ) -> None:
        """Create custom indexes for the collection."""
        with BaseMilvus.__db_switch_lock:
            db_admin_client = BaseMilvus._get_or_create_tenant_connection(tenant_code)
            existing_indexes = BaseMilvus._get_existing_indexes(
                db_admin_client, collection_name
            )

            # Create vector index
            if BaseMilvus.__VECTOR_INDEX_NAME not in existing_indexes:
                BaseMilvus._create_vector_index(
                    db_admin_client, collection_name, index_type, metric_type, nlist
                )
                summary["vector_index"] = "created"
            else:
                summary["vector_index"] = "already exists"
                logger.info(
                    f"Vector index {BaseMilvus.__VECTOR_INDEX_NAME} already exists on '{collection_name}'."
                )

            # Create sparse index
            if BaseMilvus.__SPARSE_INDEX_NAME not in existing_indexes:
                BaseMilvus._create_sparse_index(
                    db_admin_client, collection_name, drop_ratio_build
                )
                summary["sparse_index"] = "created"
            else:
                summary["sparse_index"] = "already exists"
                logger.info(
                    f"Sparse index {BaseMilvus.__SPARSE_INDEX_NAME} already exists on '{collection_name}'."
                )
            # Note: Model index removed as model field is not present in custom schema

    @staticmethod
    def _get_existing_indexes(
        db_admin_client: MilvusClient, collection_name: str
    ) -> set:
        """Get set of existing index names for collection."""
        indexes = db_admin_client.list_indexes(collection_name=collection_name)
        existing = set()
        for idx in indexes:
            if isinstance(idx, dict) and "index_name" in idx:
                existing.add(idx["index_name"])
            elif isinstance(idx, str):
                existing.add(idx)
        return existing

    @staticmethod
    def _create_vector_index(
        db_admin_client: MilvusClient,
        collection_name: str,
        index_type: str,
        metric_type: str,
        nlist: int,
    ) -> None:
        """Create vector index for collection."""
        ip = IndexParams()
        ip.add_index(
            field_name=BaseMilvus._get_vector_field_name(),
            index_type=index_type,
            index_name=BaseMilvus.__VECTOR_INDEX_NAME,
            metric_type=metric_type,
            params={"nlist": nlist},
        )
        db_admin_client.create_index(collection_name=collection_name, index_params=ip)
        logger.info(f"Custom index {BaseMilvus.__VECTOR_INDEX_NAME} created.")

    @staticmethod
    def _grant_collection_permissions(tenant_code: str, collection_name: str) -> None:
        """Grant collection permissions to tenant role."""
        role_name = BaseMilvus._get_tenant_role_name_by_tenant_code(tenant_code)
        BaseMilvus._grant_tenant_privileges_to_collection_if_not_exists(
            tenant_code=tenant_code, object_name=collection_name, role_name=role_name
        )
        logger.info(
            f"Granted permissions on collection '{collection_name}' to role '{role_name}'."
        )

    @staticmethod
    def _create_sparse_index(
        db_admin_client: MilvusClient,
        collection_name: str,
        drop_ratio_build: float = 0.1,
    ) -> None:
        """Create sparse vector index for collection."""
        # Validate drop_ratio_build parameter
        if (
            drop_ratio_build is None
            or not isinstance(drop_ratio_build, (int, float))
            or not (0.0 <= drop_ratio_build <= 1.0)
        ):
            drop_ratio_build = 0.1

        ip = IndexParams()
        ip.add_index(
            field_name="sparse_vector",
            index_type="SPARSE_INVERTED_INDEX",
            index_name=BaseMilvus.__SPARSE_INDEX_NAME,
            metric_type="IP",
            params={"drop_ratio_build": drop_ratio_build},
        )
        db_admin_client.create_index(collection_name=collection_name, index_params=ip)
        logger.info(f"Sparse index {BaseMilvus.__SPARSE_INDEX_NAME} created.")

    @staticmethod
    def _grant_collection_permissions(tenant_code: str, collection_name: str) -> None:
        """Grant collection permissions to tenant role."""
        role_name = BaseMilvus._get_tenant_role_name_by_tenant_code(tenant_code)
        BaseMilvus._grant_tenant_privileges_to_collection_if_not_exists(
            tenant_code=tenant_code, object_name=collection_name, role_name=role_name
        )
        logger.info(
            f"Granted permissions on collection '{collection_name}' to role '{role_name}'."
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

        except MilvusException as e:
            logger.error(f"Milvus error granting collection privileges: {e}")
            raise MilvusOperationError(f"Failed to grant privileges: {e}")
        except Exception as e:
            logger.error(f"Unexpected error granting collection privileges: {e}")
            raise MilvusOperationError(f"Failed to grant privileges: {e}")

    @staticmethod
    def check_connection(client: MilvusClient) -> bool:
        """
        Verify Milvus client connection health by attempting to list collections.

        Args:
            client (MilvusClient): Milvus client instance to test

        Returns:
            bool: True if connection is healthy, False otherwise
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

        except MilvusException as ex:
            logger.error(
                f"Milvus error creating collection '{collection_name}' for tenant '{tenant_code}': {ex}"
            )
            raise CollectionError(
                f"Failed to create collection '{collection_name}' for tenant '{tenant_code}': {ex}"
            )
        except Exception as ex:
            logger.error(
                f"Unexpected error creating collection '{collection_name}' for tenant '{tenant_code}': {ex}"
            )
            raise CollectionError(
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
            logger.debug(f"Roles for user '{sanitize_for_log(user_id)}': {role_names}")
            return (
                "admin" in role_names
                or APP_SETTINGS.vectordb.admin_role_name in role_names
            )
        except MilvusException as e:
            logger.error(
                f"Error checking admin role for user '{sanitize_for_log(user_id)}': {e}"
            )
            return False

    @staticmethod
    def _setup_tenant_vector_store(
        tenant_code: str, vector_dimension: int = 256, **kwargs: Any
    ) -> dict[str, Any]:
        """Sets up database, user, role, and basic permissions for a tenant."""
        summary = BaseMilvus._init_tenant_summary(tenant_code)

        try:
            BaseMilvus._create_tenant_database(tenant_code, summary)
            client_id = BaseMilvus._setup_tenant_user(tenant_code, summary, **kwargs)
            BaseMilvus._setup_tenant_role(tenant_code, client_id, summary)
            return summary
        except (MilvusException, MilvusOperationError, UserManagementError) as ex:
            logger.exception(f"Tenant setup error for tenant '{tenant_code}': {ex}")
            raise TenantError(f"Failed to setup tenant for '{tenant_code}': {ex}")
        except Exception as ex:
            logger.exception(
                f"Unexpected error setting up tenant for '{tenant_code}': {ex}"
            )
            raise TenantError(f"Failed to setup tenant for '{tenant_code}': {ex}")

    @staticmethod
    def _init_tenant_summary(tenant_code: str) -> dict[str, Any]:
        """Initialize tenant setup summary."""
        return {
            "db_created": False,
            "role_created": False,
            "role_assigned": False,
            "client_id": None,
            "client_secret": None,
            "new_client_id": False,
            "tenant_code": tenant_code,
            "message": "Tenant setup completed successfully.",
        }

    @staticmethod
    def _create_tenant_database(tenant_code: str, summary: dict) -> None:
        """Create database for tenant if it doesn't exist."""
        db_name = BaseMilvus._get_db_name_by_tenant_code(tenant_code)
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

    @staticmethod
    def _setup_tenant_user(tenant_code: str, summary: dict, **kwargs: Any) -> str:
        """Setup user for tenant, creating new one if needed."""
        current_user = BaseMilvus._get_current_user_of_a_tenant(tenant_code)
        replace_current = kwargs.get("replace_current_client_id", False)
        create_another = kwargs.get("create_another_client_id", False)

        if current_user is None or replace_current or create_another:
            return BaseMilvus._create_new_tenant_user(
                tenant_code, current_user, replace_current, summary
            )
        else:
            summary["client_id"] = current_user
            logger.debug(f"User '{current_user}' already exists.")
            return current_user

    @staticmethod
    def _create_new_tenant_user(
        tenant_code: str,
        current_user: Optional[str],
        replace_current: bool,
        summary: dict,
    ) -> str:
        """Create new user for tenant."""
        admin_client = BaseMilvus.__get_internal_admin_client()

        if current_user and replace_current:
            admin_client.drop_user(user_name=current_user)

        client_id = BaseMilvus.__generate_client_id("none", tenant_code)
        secret_key = BaseMilvus.__generate_secret_key("none")
        admin_client.create_user(user_name=client_id, password=secret_key)

        summary.update(
            {"client_id": client_id, "client_secret": secret_key, "new_client_id": True}
        )
        logger.debug(f"User '{client_id}' created successfully!")
        return client_id

    @staticmethod
    def _setup_tenant_role(tenant_code: str, client_id: str, summary: dict) -> None:
        """Setup role for tenant and assign to user."""
        role_name = BaseMilvus._get_tenant_role_name_by_tenant_code(tenant_code)

        with BaseMilvus.__db_switch_lock:
            db_admin_client = BaseMilvus._get_or_create_tenant_connection(tenant_code)
            BaseMilvus._create_tenant_role(db_admin_client, role_name, summary)
            BaseMilvus._assign_role_to_tenant_user(
                db_admin_client, client_id, role_name, summary
            )

    @staticmethod
    def _create_tenant_role(
        db_admin_client: MilvusClient, role_name: str, summary: dict
    ) -> None:
        """Create role for tenant if it doesn't exist."""
        roles = db_admin_client.list_roles()
        role_names = [r["role_name"] if isinstance(r, dict) else r for r in roles]

        if role_name not in role_names:
            db_admin_client.create_role(role_name=role_name)
            logger.info(f"Role '{role_name}' created.")
            summary["role_created"] = True
        else:
            logger.info(f"Role '{role_name}' already exists.")

    @staticmethod
    def _assign_role_to_tenant_user(
        db_admin_client: MilvusClient, client_id: str, role_name: str, summary: dict
    ) -> None:
        """Assign role to tenant user if user exists."""
        users = db_admin_client.list_users()
        user_names = [u["user_name"] if isinstance(u, dict) else u for u in users]

        if client_id in user_names:
            BaseMilvus.__assign_role_to_user(user_name=client_id, role_name=role_name)
            logger.info(f"Assigned role '{role_name}' to user '{client_id}'.")
            summary["role_assigned"] = True
        else:
            logger.warning(
                f"User '{client_id}' does not exist to assign role '{role_name}'."
            )

    @classmethod
    def _get_or_create_tenant_connection(cls, tenant_code: str) -> MilvusClient:
        """
        Gets a pooled MilvusClient instance for the given tenant.
        """
        db_name = cls._get_db_name_by_tenant_code(tenant_code)
        return milvus_pool.get_connection(
            uri=cls._get_milvus_url(),
            user=cls.__milvus_admin_username,
            password=cls.__milvus_admin_password,
            database=db_name,
        )

# =============================================================================
# File: milvus_helper.py
# Date: 2025-06-14
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

from threading import Lock
from typing import Any, List, Optional, Tuple

from app.app_init import APP_SETTINGS
from app.exceptions.custom_exceptions import (
    AuthenticationError,
    MilvusConnectionError,
    ValidationError,
    VectorStoreError,
)
from app.logger import get_logger
from app.milvus.base_milvus import BaseMilvus
from app.milvus.vector_store import VectorStore
from app.models.embedded_meta import EmbeddedMeta
from app.models.insert_request import InsertEmbeddedRequest
from app.models.reset_password_request import ResetPasswordRequest
from app.models.reset_password_response import ResetPasswordResponse
from app.models.search_request import SearchEmbeddedRequest
from app.models.set_user_request import SetUserRequest
from app.modules.concurrent_dict import ConcurrentDict
from app.utils.log_sanitizer import sanitize_for_log

logger = get_logger("milvus_helper")


class MilvusHelper(BaseMilvus):
    """
    Helper class for Milvus operations, providing thread-safe initialization,
    vector store management, and user/password operations for multi-tenant environments.
    """

    __mhelper_init_lock: Lock = Lock()
    __mhelper_initialized: bool = False
    __vector_stores: ConcurrentDict = ConcurrentDict("_vector_stores")

    def __init__(self) -> None:
        """
        Initialize the MilvusHelper instance and its base class.

        Returns:
            None
        """
        logger.debug("Initializing MilvusHelper...")
        super().__init__()

    @classmethod
    def initialize(cls, **kwargs: Any) -> None:
        """
        Initialize the Milvus admin client and set configuration (thread-safe).

        Args:
            **kwargs: Additional keyword arguments for initialization.

        Returns:
            None
        """
        with cls.__mhelper_init_lock:
            if not cls.__mhelper_initialized:
                try:
                    cls()
                    BaseMilvus._set_admin_role_if_not_exists()
                    logger.debug("MilvusHelper initialized successfully.")
                except (ConnectionError, TimeoutError) as ex:
                    logger.error(f"Connection error initializing Milvus: {ex}")
                    raise MilvusConnectionError(f"Error initializing Milvus: {ex}")
                except Exception as ex:
                    logger.error(f"Unexpected error initializing Milvus: {ex}")
                    raise MilvusConnectionError(f"Error initializing Milvus: {ex}")
                cls.__mhelper_initialized = True

    @staticmethod
    def insert_embedded_data(
        request: InsertEmbeddedRequest,
        token: str,
        **kwargs: Any,
    ) -> int:
        """
        Insert embedded vectors into the tenant's vector store.

        Args:
            request (InsertEmbeddedRequest): The request containing data to insert.
            token (str): The authentication token.
            **kwargs: Additional keyword arguments.

        Returns:
            int: Number of vectors inserted.

        Raises:
            AuthenticationError: If token is invalid.
            ValidationError: If database or collection doesn't exist.
        """
        client_id, secret_key = MilvusHelper._split_token(token)
        if not BaseMilvus._validate_token(token=token):
            logger.error("Invalid database token provided")
            raise AuthenticationError("Invalid database token.")

        # Check if database exists
        if not BaseMilvus._check_database_exists(request.tenant_code):
            raise ValidationError(
                f"Database for tenant '{request.tenant_code}' does not exist. Please run set_vector_store first."
            )

        # Check if collection exists
        if not BaseMilvus._check_collection_exists(
            request.tenant_code, request.model_name
        ):
            raise ValidationError(
                f"Collection for tenant '{request.tenant_code}' and model '{request.model_name}' does not exist. Please run generate_schema first."
            )

        tenant_store = MilvusHelper.__get_or_add_current_volumes(
            request.tenant_code, client_id, secret_key, request.model_name
        )
        logger.debug(
            f"Inserting {len(request.data)} embedded vectors into vector store for tenant '{sanitize_for_log(request.tenant_code)}' with model '{sanitize_for_log(request.model_name)}'."
        )
        # Optimize flush behavior based on configurable batch size
        batch_size = len(request.data)
        threshold = APP_SETTINGS.vectordb.auto_flush_min_batch
        if threshold == 0:
            auto_flush_by_size = True
        elif threshold > 0:
            auto_flush_by_size = batch_size >= threshold
        else:
            auto_flush_by_size = False
        kwargs["auto_flush"] = kwargs.get("force_flush", auto_flush_by_size)

        tenant_store.insert_data(request.data, **kwargs)
        return len(request.data)

    @staticmethod
    def search_embedded_data(
        request: SearchEmbeddedRequest, token: str, **kwargs: Any
    ) -> List[EmbeddedMeta]:
        """
        Search for embedded data in the tenant's vector store.

        Args:
            request (SearchEmbeddedRequest): The search request.
            token (str): The authentication token.
            **kwargs: Additional keyword arguments.

        Returns:
            List[EmbeddedMeta]: Search results.

        Raises:
            AuthenticationError: If token is invalid.
            ValidationError: If database or collection doesn't exist.
        """
        client_id, secret_key = MilvusHelper._split_token(token)
        if not BaseMilvus._validate_token(token=token):
            logger.error("Invalid database token provided")
            raise AuthenticationError("Invalid database token.")

        # Check if database exists
        if not BaseMilvus._check_database_exists(request.tenant_code):
            raise ValidationError(
                f"Database for tenant '{request.tenant_code}' does not exist. Please run set_vector_store first."
            )

        # Check if collection exists
        if not BaseMilvus._check_collection_exists(request.tenant_code, request.model):
            raise ValidationError(
                f"Collection for tenant '{request.tenant_code}' and model '{request.model}' does not exist. Please run generate_schema first."
            )

        tenant_store = MilvusHelper.__get_or_add_current_volumes(
            request.tenant_code, client_id, secret_key, request.model
        )
        logger.debug(
            f"Searching in vector store for tenant '{sanitize_for_log(request.tenant_code)}' with model '{sanitize_for_log(request.model)}'."
        )

        if getattr(request, "hybrid_search", False):
            return tenant_store.hybrid_search_store(search_request=request, **kwargs)
        else:
            return tenant_store.search_store(search_request=request, **kwargs)

    @staticmethod
    def set_user(request: SetUserRequest, token: str, **kwargs: Any) -> dict:
        """
        Set up a user for a tenant, creating all necessary resources if missing.
        Only super users can perform this operation.

        Args:
            request (SetUserRequest): The user setup request.
            token (str): The authentication token.
            **kwargs: Additional keyword arguments.

        Returns:
            dict: Summary of user setup.

        Raises:
            AuthenticationError: If token is invalid or user is not a super user.
        """
        client_id, secret_key = MilvusHelper._split_token(token)
        logger.debug(
            f"Setting up user for tenant '{sanitize_for_log(request.tenant_code)}'"
        )
        if not BaseMilvus._validate_token(token=token):
            logger.error("Invalid database token provided")
            raise AuthenticationError("Invalid database token.")
        if not BaseMilvus._is_super_user(user_id=client_id):
            logger.error(f"User '{sanitize_for_log(client_id)}' is not a super user.")
            raise AuthenticationError(
                "User is not a super user to perform this operation."
            )

        return MilvusHelper._create_user_for_tenant(
            tenant_code=request.tenant_code,
            reset_user=request.reset_user,
            token=token,
            **kwargs,
        )

    @staticmethod
    def reset_password(
        request: ResetPasswordRequest, token: str, **kwargs: Any
    ) -> ResetPasswordResponse:
        """
        Reset the password for a user in a tenant. Only super users can perform this operation.

        Args:
            request (ResetPasswordRequest): The password reset request.
            token (str): The authentication token.
            **kwargs: Additional keyword arguments.

        Returns:
            ResetPasswordResponse: Password reset result.

        Raises:
            AuthenticationError: If token is invalid or user is not a super user.
        """
        client_id, secret_key = MilvusHelper._split_token(token)
        logger.debug(
            f"Resetting password for tenant '{sanitize_for_log(request.tenant_code)}'"
        )
        if not BaseMilvus._validate_token(token=token):
            logger.error("Invalid database token provided")
            raise AuthenticationError("Invalid database token.")
        if not BaseMilvus._is_super_user(user_id=client_id):
            logger.error(f"User '{sanitize_for_log(client_id)}' is not a super user.")
            raise AuthenticationError(
                "User is not a super user to perform this operation."
            )

        return BaseMilvus._reset_admin_user_password(
            request=request,
            **kwargs,
        )

    @staticmethod
    def _split_token(token: str) -> Tuple[str, str]:
        """
        Split a token into user_id and password.

        Supports both 'user_id:password' and 'user_id|password' formats.

        Args:
            token (str): The authentication token.

        Returns:
            Tuple[str, str]: (user_id, password)

        Raises:
            ValidationError: If token format is invalid.
        """
        # Remove 'Bearer ' prefix if present
        if token.startswith("Bearer "):
            token = token[7:].strip()
        # Replace '|' with ':' for Milvus compatibility
        token = token.replace("|", ":")
        if ":" in token:
            parts = token.split(":", 1)
        else:
            raise ValidationError(
                "Invalid database token format. Expected 'user_id:password' or 'user_id|password'."
            )
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValidationError(
                "Invalid database token format. Expected 'user_id:password' or 'user_id|password'."
            )
        return parts[0], parts[1]

    @staticmethod
    def set_vector_store(tenant_code: str, token: str, **kwargs: Any) -> dict[str, Any]:
        """
        Set up database, user, role, and permissions for a tenant. Does NOT create collections or indexes.

        Args:
            tenant_code (str): The tenant code.
            token (str): The authentication token.
            **kwargs: Additional keyword arguments.

        Returns:
            dict[str, Any]: Summary of the setup operation.

        Raises:
            AuthenticationError: If the token is invalid or user is not a super user.
            ValidationError: If the tenant_code is missing.
            VectorStoreError: If initialization has not been performed.
        """
        client_id, secret_key = MilvusHelper._split_token(token)
        logger.debug(
            f"Setting up vector store for tenant '{sanitize_for_log(tenant_code)}' with client_id '{sanitize_for_log(client_id)}'."
        )
        if not BaseMilvus._validate_token(token=token):
            logger.error("Invalid database token provided")
            raise AuthenticationError("Invalid database token.")
        if not BaseMilvus._is_super_user(user_id=client_id):
            logger.error(f"User '{sanitize_for_log(client_id)}' is not a super user.")
            raise AuthenticationError("User is not a super user.")

        with MilvusHelper.__mhelper_init_lock:
            if not MilvusHelper.__mhelper_initialized:
                logger.error(
                    "MilvusHelper has not been initialized. Please call initialize() first."
                )
                raise VectorStoreError(
                    "Vector store has not been initialized properly. Please set required vector store values."
                )
            if not tenant_code:
                logger.error("tenant_code is required.")
                raise ValidationError("tenant_code is required.")

            return BaseMilvus._setup_tenant_vector_store(
                tenant_code=tenant_code, **kwargs
            )

    @staticmethod
    def generate_schema(
        tenant_code: str,
        model_name: str,
        dimension: int,
        nlist: int,
        metric_type: str,
        index_type: str,
        metadata_length: int,
        drop_ratio_build: float,
        token: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Generate a custom schema for a tenant with specified parameters.

        Args:
            tenant_code (str): The tenant code.
            model_name (str): The model name.
            dimension (int): The vector dimension.
            nlist (int): Number of clusters for IVF index.
            metric_type (str): Metric type for index.
            index_type (str): Index type.
            metadata_length (int): Metadata max length.
            drop_ratio_build (float): Drop ratio for sparse index.
            token (str): The authentication token.
            **kwargs: Additional keyword arguments.

        Returns:
            dict[str, Any]: Summary of the schema generation operation.

        Raises:
            AuthenticationError: If token is invalid or user is not a super user.
            ValidationError: If required parameters are missing.
            VectorStoreError: If schema generation fails.
        """
        client_id, secret_key = MilvusHelper._split_token(token)
        logger.debug(
            f"Generating custom schema for tenant '{sanitize_for_log(tenant_code)}' with model '{sanitize_for_log(model_name)}'."
        )

        if not BaseMilvus._validate_token(token=token):
            logger.error("Invalid database token provided")
            raise AuthenticationError("Invalid database token.")
        if not BaseMilvus._is_super_user(user_id=client_id):
            logger.error(f"User '{sanitize_for_log(client_id)}' is not a super user.")
            raise AuthenticationError("User is not a super user.")

        with MilvusHelper.__mhelper_init_lock:
            if not MilvusHelper.__mhelper_initialized:
                logger.error(
                    "MilvusHelper has not been initialized. Please call initialize() first."
                )
                raise VectorStoreError(
                    "Vector store has not been initialized properly. Please set required vector store values."
                )
            if not tenant_code:
                logger.error("tenant_code is required.")
                raise ValidationError("tenant_code is required.")
            if not model_name:
                logger.error("model_name is required.")
                raise ValidationError("model_name is required.")

            # Check if database exists
            if not BaseMilvus._check_database_exists(tenant_code):
                raise ValidationError(
                    f"Database for tenant '{tenant_code}' does not exist. Please run set_vector_store first."
                )

            return BaseMilvus._generate_custom_schema(
                tenant_code=tenant_code,
                model_name=model_name,
                dimension=dimension,
                nlist=nlist,
                metric_type=metric_type,
                index_type=index_type,
                metadata_length=metadata_length,
                drop_ratio_build=drop_ratio_build,
                **kwargs,
            )

    @staticmethod
    def flush_tenant_collection(tenant_code: str, model_name: str, token: str) -> bool:
        """
        Manually flush a specific tenant's collection.

        Args:
            tenant_code (str): The tenant code.
            model_name (str): The model name.
            token (str): The authentication token.

        Returns:
            bool: True if flush succeeded, False otherwise.
        """
        client_id, secret_key = MilvusHelper._split_token(token)
        if not BaseMilvus._validate_token(token=token):
            raise AuthenticationError("Invalid database token.")

        try:
            tenant_store = MilvusHelper.__get_or_add_current_volumes(
                tenant_code, client_id, secret_key, model_name
            )
            tenant_store.flush_collection()
            return True
        except Exception:
            return False

    @staticmethod
    def __get_or_add_current_volumes(
        tenant_id: "Optional[str]", user_id: str, password: str, model_name: str
    ) -> VectorStore:
        """
        Get or create a VectorStore instance for the given tenant/user/model.

        Args:
            tenant_id (str): The tenant ID.
            user_id (str): The user ID.
            password (str): The user's password.
            model_name (str): The model name.

        Returns:
            VectorStore: The vector store instance.
        """
        if not tenant_id:
            raise ValidationError("tenant_id is required")

        return MilvusHelper.__vector_stores.get_or_add(
            (tenant_id, user_id, model_name),
            lambda: VectorStore(tenant_id, user_id, password, model_name),
        )

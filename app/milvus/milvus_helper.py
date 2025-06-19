# =============================================================================
# File: milvus_helper.py
# Date: 2025-06-14
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

from threading import Lock
from typing import Any, List, Optional, Tuple

from app.app_init import APP_SETTINGS
from app.logger import get_logger
from app.milvus.base_milvus import BaseMilvus
from app.milvus.vector_store import VectorStore
from app.models.embeded_meta import EmbeddedMeta
from app.models.insert_request import InsertEmbeddedRequest
from app.models.search_request import SearchEmbeddedRequest
from app.models.set_user_request import SetUserRequest
from app.modules.concurrent_dict import ConcurrentDict

logger = get_logger("milvus_helper")


class MilvusHelper(BaseMilvus):
    __mhelper_init_lock: Lock = Lock()
    __mhelper_initialized: bool = False
    __vector_stores: ConcurrentDict = ConcurrentDict("_vector_stores")

    def __init__(self) -> None:
        logger.debug("Initializing MilvusHelper...")
        super().__init__()  # HINT: This calls BaseMilvus.__init__()

    @classmethod
    def initialize(cls, **kwargs: Any) -> None:
        """
        Initializes the Milvus admin client and sets configuration.
        """
        with cls.__mhelper_init_lock:
            if not cls.__mhelper_initialized:
                try:
                    cls()  # HINT: This will call __init__ and thus BaseMilvus.__init__()
                    BaseMilvus._set_admin_role_if_not_exists()
                    logger.debug("MilvusHelper initialized successfully.")
                except Exception as ex:
                    logger.error(f"Error initializing Milvus: {ex}")
                    raise ConnectionError(f"Error initializing Milvus: {ex}")
                cls.__mhelper_initialized = True

    @staticmethod
    def insert_embedded_data(
        request: InsertEmbeddedRequest,
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

        tenant_store: VectorStore = MilvusHelper.__get_or_add_current_volumes(
            request.tenant_code, client_id, secret_key
        )
        logger.debug(
            f"Inserting {len(request.data)} embedded vectors into vector store for tenant '{request.tenant_code}'."
        )
        tenant_store.insert_data(request.data, **kwargs)
        return len(request.data)

    @staticmethod
    def search_embedded_data(
        request: SearchEmbeddedRequest, token: str, **kwargs: Any
    ) -> List[EmbeddedMeta]:
        """
        Searches for embedded data in the tenant's vector store.
        """
        client_id, secret_key = MilvusHelper._split_token(token)
        valid_token = BaseMilvus._validate_token(token=token)
        if not valid_token:
            logger.error(f"Invalid token: {token}")
            raise ValueError("Invalid token.")

        tenant_store: VectorStore = MilvusHelper.__get_or_add_current_volumes(
            request.tenant_code, client_id, secret_key
        )
        return tenant_store.search_store(request=request, kwargs=kwargs)

    @staticmethod
    def set_user(request: SetUserRequest, token: str, **kwargs: Any) -> dict:
        """
        Sets up a user for a tenant, creating all necessary resources if missing.
        Uses a lock to ensure thread safety.
        """
        client_id, secret_key = MilvusHelper._split_token(token)
        logger.debug(
            f"Setting up user for tenant '{request.tenant_code}'"
        )
        valid_token = BaseMilvus._validate_token(token=token)
        if not valid_token:
            logger.error(f"Invalid token: {token}")
            raise ValueError("Invalid token.")
        super_user = BaseMilvus._is_super_user(user_id=client_id)
        if not super_user:
            logger.error(f"User '{client_id}' is not a super user.")
            raise PermissionError("User is not a super user to perform this operation.")

        return MilvusHelper._create_user_for_tenant(
            tenant_code=request.tenant_code, reset_user=request.reset_user, token=token, **kwargs
        )

    @staticmethod
    def _split_token(token: str) -> Tuple[str, str]:
        """
        Splits a token into user_id and password.
        """
        try:
            user_id, password = token.split(":", 1)  # Split at the first colon
            return user_id, password
        except ValueError:
            raise ValueError("Invalid token format. Expected 'user_id:password'.")

    @staticmethod
    def set_vector_store(
        tenant_code: str, vector_dimension: int, token: str, **kwargs: Any
    ) -> dict[str, Any]:
        """
        Sets up a vector store for a tenant, creating all necessary resources if missing.

        Args:
            tenant_code (str): The tenant identifier.
            vector_dimension (int): The dimension of the vector store.
            token (str): The authentication token.
            **kwargs: Additional keyword arguments.

        Returns:
            dict[str, Any]: Summary of the setup operation.

        Raises:
            ValueError: If the token or tenant_code is invalid.
            PermissionError: If the user is not a super user.
            Exception: If initialization has not been performed.
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
                f"Setting up vector store for tenant '{tenant_code}' with client_id '{client_id}'."
            )
            return BaseMilvus._setup_tenant_vector_store(
                tenant_code=tenant_code, vector_dimension=vector_dimension, **kwargs
            )

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

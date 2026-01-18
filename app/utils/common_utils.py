# =============================================================================
# File: common_utils.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================


from typing import Any, Dict, Type, TypeVar, Union

from pydantic import BaseModel

# Generic type variable for Pydantic models
T = TypeVar("T", bound=BaseModel)


class CommonUtils:
    """
    Utility class for common dictionary and request operations.
    Provides type-safe helpers for working with Pydantic models and dictionaries.
    """

    @staticmethod
    def get_value_from_kwargs(key: str, **kwargs: Any) -> Any:
        """
        Get a value from kwargs by key.

        Args:
            key: The key to look up.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            The value for the key if present, else None.

        Example:
            >>> CommonUtils.get_value_from_kwargs("timeout", timeout=30, retries=3)
            30
        """
        return kwargs.get(key, None)

    @staticmethod
    def add_missing_from_other(
        target: Dict[str, Any], source: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Add only missing key-value pairs from source to target dict.
        Existing keys in target are not overwritten.

        Args:
            target: The target dictionary to update.
            source: The source dictionary to copy from.

        Returns:
            The updated target dictionary (same object as input).

        Example:
            >>> target = {"a": 1}
            >>> source = {"b": 2, "a": 99}
            >>> result = CommonUtils.add_missing_from_other(target, source)
            >>> result
            {"a": 1, "b": 2}  # "a" kept original value
        """
        for key, value in source.items():
            if key not in target:
                target[key] = value
        return target

    @staticmethod
    def parse_extra_fields(
        request: Union[BaseModel, Dict[str, Any]], model_class: Type[T]
    ) -> Dict[str, Any]:
        """
        Extract extra fields from a request that are not defined in the model class.

        This is useful for detecting and capturing unexpected fields in API requests
        that don't match the expected Pydantic model schema.

        Args:
            request: The request object (Pydantic model instance or dict).
            model_class: The Pydantic model class to use as schema reference.

        Returns:
            Dictionary of extra fields not defined in the model schema.

        Raises:
            AttributeError: If model_class is not a valid Pydantic model.

        Example:
            >>> from pydantic import BaseModel
            >>> class User(BaseModel):
            ...     name: str
            ...     email: str
            >>> request = {"name": "John", "email": "john@example.com", "extra": "value"}
            >>> extra = CommonUtils.parse_extra_fields(request, User)
            >>> extra
            {"extra": "value"}
        """
        # Get all fields defined in the model (Pydantic v2 compatibility)
        if hasattr(model_class, "model_fields"):
            model_fields = set(model_class.model_fields.keys())
        else:
            model_fields = set(model_class.__fields__.keys())

        # Convert request to dict (Pydantic v2 compatibility)
        if hasattr(request, "model_dump"):
            req_dict = request.model_dump()
        elif hasattr(request, "dict"):
            req_dict = request.dict()
        else:
            req_dict = dict(request)

        # Extract extra fields
        return {k: v for k, v in req_dict.items() if k not in model_fields}

    @staticmethod
    def validate_tenant_match(client_id: str, header_tcode: str, payload_tcode: str) -> None:
        """Validate tenant code consistency between header and payload.

        Raises HTTPException (400) on mismatch for non-superadmin clients.

        Args:
            client_id: the authenticated client's id (or None)
            header_tcode: tenant code from the header or None/empty
            payload_tcode: tenant code from the payload or None/empty
        """
        from fastapi import HTTPException, status

        from app.modules.key_manager import key_manager

        h = header_tcode or None
        p = payload_tcode or None
        if not key_manager.is_super_admin(client_id):
            if p and h and p != h:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Mismatched tenant_code between header and payload/query parameter",
                )

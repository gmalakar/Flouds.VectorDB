# =============================================================================
# File: common_utils.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================


from typing import Any, Dict


class CommonUtils:
    """
    Utility class for common dictionary and request operations.
    """

    @staticmethod
    def get_value_from_kwargs(key: str, **kwargs) -> Any:
        """
        Get a value from kwargs by key.

        Args:
            key: The key to look up.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            The value for the key if present, else None.
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
            target (dict): The target dictionary to update.
            source (dict): The source dictionary to copy from.

        Returns:
            dict: The updated target dictionary.
        """
        for key, value in source.items():
            if key not in target:
                target[key] = value
        return target

    @staticmethod
    def parse_extra_fields(request: Any, model_class: Any) -> Dict[str, Any]:
        """
        Extract extra fields from a request that are not defined in the model class.

        Args:
            request: The request object (Pydantic model or dict).
            model_class: The Pydantic model class.

        Returns:
            dict: Dictionary of extra fields not defined in the model.
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
    def validate_tenant_match(client_id, header_tcode: str, payload_tcode: str) -> None:
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

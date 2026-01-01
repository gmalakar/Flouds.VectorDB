# =============================================================================
# File: common_utils.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================


class CommonUtils:
    """
    Utility class for common dictionary and request operations.
    """

    @staticmethod
    def get_value_from_kwargs(key, **kwargs):
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
    def add_missing_from_other(target: dict, source: dict) -> dict:
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
    def parse_extra_fields(request, model_class):
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

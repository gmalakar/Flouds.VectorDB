# =============================================================================
# File: utilities.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================


class CommonUtils:
    @staticmethod
    def get_value_from_kwargs(key, **kwargs):
        return kwargs.get(key, None)

    @staticmethod
    def add_missing_from_other(target: dict, source: dict) -> dict:
        """
        Adds only missing key-value pairs from source to target dict.
        Existing keys in target are not overwritten.
        Returns the updated target dict.
        """
        for key, value in source.items():
            if key not in target:
                target[key] = value
        return target

    @staticmethod
    def parse_extra_fields(request, model_class):
        # Get all fields defined in the model
        model_fields = set(model_class.__fields__.keys())
        # Convert request to dict (if it's a Pydantic model)
        req_dict = request.dict() if hasattr(request, "dict") else dict(request)
        # Extract extra fields
        return {k: v for k, v in req_dict.items() if k not in model_fields}

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
    def parse_extra_fields(request_obj, base_model_cls):
        """
        Extracts extra fields from a Pydantic request object that are not defined in the base model.
        Returns a dict of extra fields.
        """
        return {
            k: v
            for k, v in request_obj.__dict__.items()
            if k not in base_model_cls.__fields__
        }

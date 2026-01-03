# =============================================================================
# File: config_request.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import re
from typing import Optional

from pydantic import Field, field_validator

from app.models.base_request import BaseRequest


class ConfigRequest(BaseRequest):
    """Request model for config operations.

    Fields:
      - key: config key (composite PK includes tenant_code)
      - value: config value (string; JSON-encode structured data before sending)
      - tenant_code: optional tenant code (inherited from BaseRequest)
      - encrypted: optional flag indicating value is stored encrypted
    """

    key: str = Field(..., description="The config key.")  # type: ignore
    value: str = Field(..., description="The config value.")  # type: ignore
    encrypted: Optional[bool] = Field(False, description="Is the value encrypted?")

    @field_validator("key")
    @classmethod
    def validate_key(cls, v: Optional[str]) -> str:
        """Validate the `key` field.

        Rules:
        - length between 1 and 128 characters
        - no whitespace characters
        - must match allowed characters: letters, digits, underscore, dot, colon, hyphen
        """
        if v is None:
            raise ValueError("Missing key")
        if not (1 <= len(v) <= 128):
            raise ValueError("key must be between 1 and 128 characters long")
        if any(ch.isspace() for ch in v):
            raise ValueError("key must not contain whitespace characters")
        if not re.match(r"^[A-Za-z0-9_.:-]+$", v):
            raise ValueError(
                "key contains invalid characters; allowed are letters, digits, underscore (_), dot (.), colon (:), and hyphen (-)"
            )
        return v

    @field_validator("value")
    @classmethod
    def validate_value_length(cls, v: Optional[str]) -> Optional[str]:
        """Enforce maximum length for config `value`.

        Limit chosen to 64KB to avoid extremely large blobs being stored
        inadvertently via the config API. Adjust if you have larger needs.
        """
        if v is None:
            return v
        max_len = 65536
        if len(v) > max_len:
            raise ValueError(f"value must be at most {max_len} characters long")
        return v

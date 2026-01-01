# =============================================================================
# File: base_request.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.utils.input_validator import validate_tenant_code


class BaseRequest(BaseModel):
    """
    Base request model for Milvus database operations.

    Attributes:
        tenant_code (str): The tenant for which the request is made.
    """

    tenant_code: str = Field(
        ...,
        description="The tenant for which the request is made. This field is required.",
    )

    model_config = ConfigDict(extra="allow")

    @field_validator("tenant_code")
    @classmethod
    def validate_tenant_code_field(cls, v: str) -> str:
        """
        Validate the tenant_code field using the custom validator.

        Args:
            v (str): The tenant code value to validate.

        Returns:
            str: The validated tenant code.
        """
        return validate_tenant_code(v)

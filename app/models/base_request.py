# =============================================================================
# File: base_request.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.utils.input_validator import validate_tenant_code


class BaseRequest(BaseModel):
    """
    Request model for milvus database operations.
    This model serves as a base for all request models, providing common fields
    """

    tenant_code: str = Field(
        ...,
        description="The tenant for which the request is made. This field is required.",
    )

    model_config = ConfigDict(extra="allow")

    @field_validator("tenant_code")
    @classmethod
    def validate_tenant_code_field(cls, v):
        return validate_tenant_code(v)

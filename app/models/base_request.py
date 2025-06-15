# =============================================================================
# File: base_request.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

from pydantic import BaseModel, Field


class BaseRequest(BaseModel):
    """
    Request model for milvus database operations.
    This model serves as a base for all request models, providing common fields
    """

    tenant_code: str = Field(
        ...,
        description="The tenant for which the request is made. This field is required.",
    )

    class Config:
        extra = "allow"  # This allows extra fields (i.e., **kwargs)

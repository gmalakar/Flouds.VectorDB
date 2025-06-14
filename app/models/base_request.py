# =============================================================================
# File: base_request.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

from pydantic import BaseModel, Field


class BaseRequest(BaseModel):
    """
    Request model for text summarization.
    """

    for_tenant: str = Field(
        ...,
        description="The tenant for which the request is made. This field is required.",
    )
    token: str = Field(
        ...,
        description="The token for authentication. This field is required.",
    )

    class Config:
        extra = "allow"  # This allows extra fields (i.e., **kwargs)

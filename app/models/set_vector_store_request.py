# =============================================================================
# File: embedding_request.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

from pydantic import Field

from app.models.base_request import BaseRequest


class SetVectorStoreRequest(BaseRequest):
    """
    Request model for text embedding.
    """

    vector_dimension: int = Field(
        ...,
        ge=1,
        le=4096,
        description="The dimension of the vector to be stored (1-4096).",
    )

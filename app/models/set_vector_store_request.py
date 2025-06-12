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
        ..., description="The dimension of the vector to be stored."
    )

    client_id: str = Field(
        ...,
        description="The client ID for which the vector store is being set. This field is required.",
    )

    client_secret: str = Field(
        ...,
        description="The client secret for authentication. This field is required.",
    )

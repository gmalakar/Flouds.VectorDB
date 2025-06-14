# =============================================================================
# File: embedding_request.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

from pydantic import Field

from app.models.base_request import BaseRequest
from app.models.embeded_vectors import EmbeddedVectors


class InsertEmbeddedRequest(BaseRequest):
    """
    Request model for text embedding.
    """

    data: list[EmbeddedVectors] = Field(
        ...,
        description="The vector to be stored in the vector store. This field is required.",
    )

# =============================================================================
# File: embedded_meta.py
# Date: 2025-06-14
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

from pydantic import BaseModel, Field


class EmbeddedMeta(BaseModel):
    """
    Model representing a text chunk and its associated metadata for embeddings.

    Attributes:
        content (str): The text chunk.
        meta (dict): The metadata associated with the embedding.
    """

    content: str = Field(..., description="The text chunk.")
    meta: dict = Field(..., description="The metadata associated with the embedding.")

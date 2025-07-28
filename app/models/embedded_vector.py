# =============================================================================
# File: embedded_vector.py
# Date: 2025-06-14
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

from typing import List

from pydantic import BaseModel, Field


class EmbeddedVector(BaseModel):
    key: str = Field(..., description="The primary key.")
    chunk: str = Field(..., description="The text chunk.")
    model: str = Field(..., description="The model used for embedding.")
    metadata: dict = Field(
        None,
        description="Metadata associated with the embedding, such as source or context.",
    )
    vector: List[float] = Field(..., description="The embedding vector values.")
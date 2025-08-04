# =============================================================================
# File: embedded_vector.py
# Date: 2025-06-14
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

from typing import List

from pydantic import BaseModel, Field, field_validator

from app.utils.input_validator import sanitize_text_input, validate_model_name


class EmbeddedVector(BaseModel):
    key: str = Field(..., description="The primary key.")
    chunk: str = Field(..., description="The text chunk.")
    model: str = Field(..., description="The model used for embedding.")
    metadata: dict = Field(
        None,
        description="Metadata associated with the embedding, such as source or context.",
    )
    vector: List[float] = Field(..., description="The embedding vector values.")

    @field_validator("key")
    @classmethod
    def validate_key_field(cls, v):
        if not v or not v.strip():
            raise ValueError("Key cannot be empty")
        return sanitize_text_input(v.strip(), max_length=256)

    @field_validator("chunk")
    @classmethod
    def validate_chunk_field(cls, v):
        if not v or not v.strip():
            raise ValueError("Chunk cannot be empty")
        return sanitize_text_input(v, max_length=60000)

    @field_validator("model")
    @classmethod
    def validate_model_field(cls, v):
        return validate_model_name(v)

    @field_validator("vector")
    @classmethod
    def validate_vector_field(cls, v):
        if not v or len(v) == 0:
            raise ValueError("Vector cannot be empty")
        if len(v) > 4096:  # Reasonable vector dimension limit
            raise ValueError("Vector dimension too large (max 4096)")
        return v

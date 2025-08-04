# =============================================================================
# File: insert_request.py
# Description: Pydantic model for vector insertion requests with validation
# Author: Goutam Malakar
# Date: 2025-01-15
# Version: 1.0.0
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

from typing import List

from pydantic import Field, field_validator, model_validator

from app.models.base_request import BaseRequest
from app.models.embedded_vector import EmbeddedVector
from app.utils.input_validator import (
    sanitize_text_input,
    validate_model_name,
    validate_vector,
)


class InsertEmbeddedRequest(BaseRequest):
    """
    Request model for inserting embedded vectors into the vector store.

    Contains the model name and list of embedded vectors with metadata
    to be stored in the tenant's vector database.
    """

    model_name: str = Field(
        ...,
        description="The model name for the vectors. This field is required.",
    )

    data: List[EmbeddedVector] = Field(
        ...,
        description="The vectors to be stored in the vector store. This field is required.",
    )

    @field_validator("model_name")
    @classmethod
    def validate_model_name_field(cls, v):
        return validate_model_name(v)

    @field_validator("data")
    @classmethod
    def validate_data_field(cls, v):
        if not v or len(v) == 0:
            raise ValueError("Data list cannot be empty")
        if len(v) > 1000:
            raise ValueError("Maximum 1000 vectors per request")

        # Validate each vector
        for i, item in enumerate(v):
            if hasattr(item, "vector") and item.vector:
                try:
                    validate_vector(item.vector)
                except ValueError as e:
                    raise ValueError(f"Invalid vector at index {i}: {e}")

            if hasattr(item, "chunk") and item.chunk:
                if len(item.chunk) > 60000:
                    raise ValueError(
                        f"Chunk at index {i} exceeds maximum length of 60000 characters"
                    )

        return v

    @model_validator(mode="after")
    def check_unique_keys(self):
        keys = [v.key for v in self.data]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate primary key values found in the data.")
        if any(not k or not str(k).strip() for k in keys):
            raise ValueError("All primary key values must be non-empty.")
        return self

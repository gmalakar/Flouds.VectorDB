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
    validate_model_name,
    validate_vector,
)


class InsertEmbeddedRequest(BaseRequest):
    """
    Request model for inserting embedded vectors into the vector store.

    Attributes:
        model_name (str): The model name for the vectors.
        data (List[EmbeddedVector]): The vectors to be stored in the vector store.
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
    def validate_model_name_field(cls, v: str) -> str:
        """
        Validate the model_name field using the custom model name validator.

        Args:
            v (str): The model name to validate.

        Returns:
            str: The validated model name.
        """
        return validate_model_name(v)

    @field_validator("data")
    @classmethod
    def validate_data_field(cls, v: list) -> list:
        """
        Validate the data field to ensure it is a non-empty list of valid vectors.

        Args:
            v (list): The list of EmbeddedVector objects to validate.

        Returns:
            list: The validated list of EmbeddedVector objects.

        Raises:
            ValueError: If the list is empty, too large, or contains invalid vectors.
        """
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
        """
        Validate that all primary keys in the data are unique and non-empty.

        Returns:
            InsertEmbeddedRequest: The validated request object.

        Raises:
            ValueError: If duplicate or empty primary keys are found.
        """
        keys = [v.key for v in self.data]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate primary key values found in the data.")
        if any(not k or not str(k).strip() for k in keys):
            raise ValueError("All primary key values must be non-empty.")
        return self

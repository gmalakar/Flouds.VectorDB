# =============================================================================
# File: embedding_request.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

from typing import List

from pydantic import Field, model_validator

from app.models.base_request import BaseRequest
from app.models.embeded_vector import EmbeddedVector


class InsertEmbeddedRequest(BaseRequest):
    """
    Request model for text embedding.
    """

    data: List[EmbeddedVector] = Field(
        ...,
        description="The vectors to be stored in the vector store. This field is required.",
    )

    @model_validator(mode="after")
    def check_unique_keys(self):
        keys = [v.key for v in self.data]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate primary key values found in the data.")
        if any(not k or not str(k).strip() for k in keys):
            raise ValueError("All primary key values must be non-empty.")
        return self

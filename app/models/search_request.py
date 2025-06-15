# =============================================================================
# File: embedding_request.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

from pydantic import Field

from app.models.base_request import BaseRequest
from app.models.embeded_vectors import EmbeddedVectors


class SearchEmbeddedRequest(BaseRequest):
    """
    Request model for text embedding.
    """

    model: str = Field(
        ...,
        description="The name of the model to be used for searching. This field is required.",
    )

    limit: int = Field(
        10,
        ge=1,
        le=10000,
        description="The maximum number of results to return. Default is 10, minimum is 1, and maximum is 1000.",
    )

    offset: int = Field(
        0,
        ge=0,
        le=10000,
        description="The offset for pagination. Default is 0, minimum is 0.",
    )

    nprobe: int = Field(
        10,
        ge=1,
        le=100,
        description="The number of probes to use for the search. Default is 1610, minimum is 1, and maximum is 100.",
    )

    round_decimal: int = Field(
        -1,
        ge=-1,
        le=6,
        description="The number of decimal places to round the results. Default is 2, minimum is 1, and maximum is 6.",
    )

    score_threshold: float = Field(
        0.8,
        ge=0.0,
        description="The minimum score threshold for results. Default is 0.8, minimum is 0.0.",
    )

    metric_type: str = Field(
        "L2",
        description="The metric type to be used for the search. Default is 'L2'.",
    )

    vector: list[float] = Field(
        ...,
        description="The vector to be searched in the vector store. This field is required.",
    )

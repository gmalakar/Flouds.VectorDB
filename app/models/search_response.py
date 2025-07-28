# =============================================================================
# File: embedding_response.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

from typing import List

from pydantic import Field

from app.models.base_response import BaseResponse
from app.models.embedded_meta import EmbeddedMeta


class SearchEmbeddedResponse(BaseResponse):
    """
    Response model for text embedding search.
    """

    """
    Request model for text embedding.
    """
    model: str = Field(
        description="The name of the model to be used for searching. This field is required.",
    )

    limit: int = Field(
        description="The maximum number of results to return. Default is 10, minimum is 1, and maximum is 1000.",
    )

    offset: int = Field(
        description="The offset for pagination. Default is 0, minimum is 0.",
    )

    nprobe: int = Field(
        description="The number of probes to use for the search. Default is 1610, minimum is 1, and maximum is 100.",
    )

    round_decimal: int = Field(
        description="The number of decimal places to round the results. Default is 2, minimum is 1, and maximum is 6.",
    )

    score_threshold: float = Field(
        description="The minimum score threshold for results. Default is 0.0, minimum is 0.0.",
    )

    metric_type: str = Field(
        description="The metric type to be used for the search. Default is 'L2'.",
    )
    data: List[EmbeddedMeta] = Field(
        ..., description="The list of embedded vectors returned from the search."
    )

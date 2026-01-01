# =============================================================================
# File: search_base.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

from typing import List, Optional

from pydantic import BaseModel, Field


class SearchEmbeddedBase(BaseModel):
    """
    Base model with common properties for search request and response.

    Attributes:
        model (str): The name of the model for searching.
        limit (int): The maximum number of results.
        offset (int): The offset for pagination.
        nprobe (int): The number of probes for the search.
        round_decimal (int): The number of decimal places for rounding results.
        consistency_level (str): The consistency level for the search.
        output_fields (List[str]): The fields included in the search results.
        score_threshold (float): The minimum score threshold for results.
        meta_required (bool): Whether metadata is required in the search results.
        metric_type (str): The metric type for the search.
        text_filter (Optional[str]): Text filter to search within chunk content.
        minimum_words_match (int): Minimum number of words to match in chunk content.
        include_stop_words (bool): Whether to include stop words in the matching process.
        increase_limit_for_text_search (int): Limit increase for text embedding search.
        hybrid_search (bool): Whether to perform hybrid search using both dense and sparse vectors.
    """

    model: str = Field(
        description="The name of the model for searching.",
    )

    limit: int = Field(
        description="The maximum number of results.",
    )

    offset: int = Field(
        description="The offset for pagination.",
    )

    nprobe: int = Field(
        description="The number of probes for the search.",
    )

    round_decimal: int = Field(
        description="The number of decimal places for rounding results.",
    )

    consistency_level: str = Field(
        description="The consistency level for the search.",
    )

    output_fields: List[str] = Field(
        description="The fields included in the search results.",
    )

    score_threshold: float = Field(
        description="The minimum score threshold for results.",
    )

    meta_required: bool = Field(
        description="Whether metadata is required in the search results.",
    )

    metric_type: str = Field(
        description="The metric type for the search.",
    )

    text_filter: Optional[str] = Field(
        description="Text filter to search within chunk content.",
    )

    minimum_words_match: int = Field(
        description="Minimum number of words to match in chunk content.",
    )

    include_stop_words: bool = Field(
        description="Whether to include stop words in the matching process.",
    )

    increase_limit_for_text_search: int = Field(
        description="Limit increase for text embedding search.",
    )

    hybrid_search: bool = Field(
        description="Whether to perform hybrid search using both dense and sparse vectors.",
    )

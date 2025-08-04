# =============================================================================
# File: search_request.py
# Description: Pydantic models for vector search requests with validation
# Author: Goutam Malakar
# Date: 2025-01-15
# Version: 1.0.0
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

from pydantic import Field, field_validator

from app.models.base_request import BaseRequest
from app.models.search_base import SearchEmbeddedBase
from app.utils.input_validator import (
    sanitize_text_input,
    validate_limit,
    validate_model_name,
    validate_offset,
    validate_score_threshold,
    validate_vector,
)


class SearchEmbeddedRequest(BaseRequest, SearchEmbeddedBase):
    """
    Request model for vector similarity search operations.

    Inherits from BaseRequest for tenant information and SearchEmbeddedBase
    for common search parameters. Supports both dense and hybrid search modes.
    """

    model: str = Field(
        ...,
        description="The name of the model to be used for searching. This field is required.",
    )

    limit: int = Field(
        10,
        ge=1,
        le=100,
        description="Maximum number of search results to return. Range: 1-100, default: 10.",
    )

    offset: int = Field(
        0,
        ge=0,
        le=100,
        description="Number of results to skip for pagination. Range: 0-100, default: 0.",
    )

    nprobe: int = Field(
        4,
        ge=4,
        le=128,
        description="The number of probes to use for the search. Default is 4, minimum is 4, and maximum is 128.",
    )

    round_decimal: int = Field(
        -1,
        ge=-1,
        le=6,
        description="Decimal places for score rounding. -1 for no rounding, 0-6 for precision, default: -1.",
    )

    consistency_level: str = Field(
        "Bounded",
        description="The consistency level for the search. Default is 'Bounded'.",
    )

    output_fields: list[str] = Field(
        ["chunk", "meta"],
        description="The fields to be included in the search results. Default includes 'chunk' and 'meta'.",
    )

    score_threshold: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score threshold for results. Range: 0.0-1.0, default: 0.0.",
    )

    meta_required: bool = Field(
        False,
        description="Whether to include metadata in the search results. Default is False.",
    )

    metric_type: str = Field(
        "COSINE",
        description="Distance metric for similarity calculation. Options: 'L2', 'IP', 'COSINE'. Default: 'COSINE'.",
    )

    text_filter: str = Field(
        None,
        description="Optional text filter for keyword-based filtering within chunk content. Used in hybrid search.",
    )

    minimum_words_match: int = Field(
        2,
        ge=1,
        le=10,
        description="Minimum number of words that must match in text filter. Range: 1-10, default: 2.",
    )

    include_stop_words: bool = Field(
        False,
        description="Whether to include stop words in the matching process.",
    )

    increase_limit_for_text_search: int = Field(
        10,
        ge=0,
        le=100,
        description="Additional results to fetch for text filtering before applying limit. Range: 0-100, default: 10.",
    )

    vector: list[float] = Field(
        ...,
        description="The vector to be searched in the vector store. This field is required.",
    )

    @field_validator("model")
    @classmethod
    def validate_model_field(cls, v):
        return validate_model_name(v)

    @field_validator("text_filter")
    @classmethod
    def validate_text_filter_field(cls, v):
        if v is not None:
            return sanitize_text_input(v, max_length=500)
        return v

    @field_validator("vector")
    @classmethod
    def validate_vector_field(cls, v):
        return validate_vector(v)

    @field_validator("metric_type")
    @classmethod
    def validate_metric_type_field(cls, v):
        allowed_metrics = ["L2", "IP", "COSINE"]
        if v not in allowed_metrics:
            raise ValueError(f"Metric type must be one of: {allowed_metrics}")
        return v

    @field_validator("consistency_level")
    @classmethod
    def validate_consistency_level_field(cls, v):
        allowed_levels = ["Strong", "Session", "Bounded", "Eventually"]
        if v not in allowed_levels:
            raise ValueError(f"Consistency level must be one of: {allowed_levels}")
        return v

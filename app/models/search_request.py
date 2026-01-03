# =============================================================================
# File: search_request.py
# Description: Pydantic models for vector search requests with validation
# Author: Goutam Malakar
# Date: 2025-01-15
# Version: 1.0.0
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

from typing import Dict, Optional

from pydantic import Field, field_validator

from app.models.base_request import BaseRequest
from app.models.search_base import SearchEmbeddedBase
from app.utils.input_validator import (
    sanitize_text_input,
    validate_model_name,
    validate_vector,
)


class SearchEmbeddedRequest(BaseRequest, SearchEmbeddedBase):
    """
    Request model for vector similarity search operations.

    Inherits from BaseRequest for tenant information and SearchEmbeddedBase
    for common search parameters. Supports both dense and hybrid search modes.

    Attributes:
        model (str): The name of the model to be used for searching.
        limit (int): Maximum number of search results to return.
        offset (int): Number of results to skip for pagination.
        nprobe (int): The number of probes to use for the search.
        round_decimal (int): Decimal places for score rounding.
        consistency_level (str): The consistency level for the search.
        output_fields (list[str]): The fields to be included in the search results.
        score_threshold (float): Minimum similarity score threshold for results.
        meta_required (bool): Whether to include metadata in the search results.
        metric_type (str): Distance metric for similarity calculation.
        text_filter (str): Optional text filter for keyword-based filtering within chunk content.
        minimum_words_match (int): Minimum number of words that must match in text filter.
        include_stop_words (bool): Whether to include stop words in the matching process.
        increase_limit_for_text_search (int): Additional results to fetch for text filtering before applying limit.
        vector (list[float]): The vector to be searched in the vector store.
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

    meta_filter: Optional[Dict[str, str]] = Field(
        default=None,
        description="Optional metadata filters (key/value substring match, case-insensitive).",
    )

    metric_type: str = Field(
        "COSINE",
        description="Distance metric for similarity calculation. Options: 'L2', 'IP', 'COSINE'. Default: 'COSINE'.",
    )

    text_filter: Optional[str] = Field(
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
    def validate_model_field(cls, v: str) -> str:
        """
        Validate the model field using the custom model name validator.

        Args:
            v (str): The model name to validate.

        Returns:
            str: The validated model name.
        """
        return validate_model_name(v)

    @field_validator("text_filter")
    @classmethod
    def validate_text_filter_field(cls, v: str) -> str:
        """
        Validate the text_filter field to ensure it is sanitized and within length limits.

        Args:
            v (str): The text filter value to validate.

        Returns:
            str: The sanitized text filter.
        """
        if v is not None:
            return sanitize_text_input(v, max_length=500)
        return v

    @field_validator("meta_filter")
    @classmethod
    def validate_meta_filter(
        cls, v: Optional[Dict[str, str]]
    ) -> Optional[Dict[str, str]]:
        """Ensure meta_filter is small and string-coercible."""
        if v is None:
            return v
        if not isinstance(v, dict):
            raise ValueError("meta_filter must be a dictionary")
        if len(v) > 10:
            raise ValueError("meta_filter supports up to 10 keys")
        cleaned = {}
        for key, val in v.items():
            if not isinstance(key, str) or not key.strip():
                raise ValueError("meta_filter keys must be non-empty strings")
            sval = str(val)
            if len(sval) > 200:
                raise ValueError("meta_filter values must be <=200 characters")
            cleaned[key.strip()] = sval
        return cleaned

    @field_validator("vector")
    @classmethod
    def validate_vector_field(cls, v: list) -> list:
        """
        Validate the vector field using the custom vector validator.

        Args:
            v (list): The vector to validate.

        Returns:
            list: The validated vector.
        """
        return validate_vector(v)

    @field_validator("metric_type")
    @classmethod
    def validate_metric_type_field(cls, v: str) -> str:
        """
        Validate the metric_type field to ensure it is one of the allowed values.

        Args:
            v (str): The metric type to validate.

        Returns:
            str: The validated metric type.

        Raises:
            ValueError: If the metric type is not allowed.
        """
        allowed_metrics = ["L2", "IP", "COSINE"]
        if v not in allowed_metrics:
            raise ValueError(f"Metric type must be one of: {allowed_metrics}")
        return v

    @field_validator("consistency_level")
    @classmethod
    def validate_consistency_level_field(cls, v: str) -> str:
        """
        Validate the consistency_level field to ensure it is one of the allowed values.

        Args:
            v (str): The consistency level to validate.

        Returns:
            str: The validated consistency level.

        Raises:
            ValueError: If the consistency level is not allowed.
        """
        allowed_levels = ["Strong", "Session", "Bounded", "Eventually"]
        if v not in allowed_levels:
            raise ValueError(f"Consistency level must be one of: {allowed_levels}")
        return v

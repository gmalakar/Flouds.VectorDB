# =============================================================================
# File: generate_schema_request.py
# Date: 2025-06-14
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

from pydantic import Field, field_validator

from app.models.base_request import BaseRequest
from app.utils.input_validator import validate_model_name, validate_vector_dimension


class GenerateSchemaRequest(BaseRequest):
    """
    Request model for generating schema with custom parameters.
    """

    dimension: int = Field(
        ...,
        ge=1,
        le=4096,
        description="The dimension of the vector to be stored (1-4096).",
    )
    nlist: int = Field(
        default=1024,
        ge=1,
        le=65536,
        description="Number of cluster units for IVF index (1-65536).",
    )
    metric_type: str = Field(
        default="COSINE",
        description="Metric type for similarity calculation (COSINE, L2, IP).",
    )
    index_type: str = Field(
        default="IVF_FLAT",
        description="Index type for vector search (IVF_FLAT, IVF_SQ8, etc.).",
    )
    model_name: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Model name to be included in schema name.",
    )
    metadata_length: int = Field(
        default=4096,
        ge=256,
        le=65535,
        description="Maximum length for metadata field (256-65535).",
    )

    @field_validator("model_name")
    @classmethod
    def validate_model_name_field(cls, v):
        return validate_model_name(v)

    @field_validator("dimension")
    @classmethod
    def validate_dimension_field(cls, v):
        return validate_vector_dimension(v)

    @field_validator("metric_type")
    @classmethod
    def validate_metric_type_field(cls, v):
        allowed_metrics = ["COSINE", "L2", "IP"]
        if v not in allowed_metrics:
            raise ValueError(f"Metric type must be one of: {allowed_metrics}")
        return v

    @field_validator("index_type")
    @classmethod
    def validate_index_type_field(cls, v):
        allowed_types = ["IVF_FLAT", "IVF_SQ8", "IVF_PQ", "HNSW"]
        if v not in allowed_types:
            raise ValueError(f"Index type must be one of: {allowed_types}")
        return v

# =============================================================================
# File: test_models.py
# Date: 2025-08-01
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import pytest
from pydantic import ValidationError

from app.models.embedded_vector import EmbeddedVector
from app.models.generate_schema_request import GenerateSchemaRequest
from app.models.insert_request import InsertEmbeddedRequest
from app.models.search_request import SearchEmbeddedRequest


class TestModels:

    def test_insert_request_valid(self):
        vector_data = EmbeddedVector(
            key="test_key",
            chunk="test chunk",
            model="test_model",
            vector=[0.1, 0.2, 0.3],
            metadata={"source": "test"},
        )

        request = InsertEmbeddedRequest(
            tenant_code="test_tenant", model_name="test_model", data=[vector_data]
        )

        assert request.tenant_code == "test_tenant"
        assert request.model_name == "test_model"
        assert len(request.data) == 1

    def test_insert_request_invalid_tenant(self):
        vector_data = EmbeddedVector(
            key="test_key",
            chunk="test chunk",
            model="test_model",
            vector=[0.1, 0.2, 0.3],
            metadata={},
        )

        with pytest.raises(ValidationError):
            InsertEmbeddedRequest(
                tenant_code="ab",  # Too short
                model_name="test_model",
                data=[vector_data],
            )

    def test_insert_request_too_many_vectors(self):
        vector_data = EmbeddedVector(
            key="test_key",
            chunk="test chunk",
            model="test_model",
            vector=[0.1, 0.2, 0.3],
            metadata={},
        )

        with pytest.raises(ValidationError):
            InsertEmbeddedRequest(
                tenant_code="test_tenant",
                model_name="test_model",
                data=[vector_data] * 1001,  # Too many vectors
            )

    def test_search_request_valid(self):
        request = SearchEmbeddedRequest(
            tenant_code="test_tenant",
            model="test_model",
            vector=[0.1, 0.2, 0.3],
            limit=10,
            metric_type="COSINE",
            hybrid_search=False,
        )

        assert request.tenant_code == "test_tenant"
        assert request.model == "test_model"
        assert request.limit == 10
        assert request.metric_type == "COSINE"

    def test_search_request_invalid_metric(self):
        with pytest.raises(ValidationError):
            SearchEmbeddedRequest(
                tenant_code="test_tenant",
                model="test_model",
                vector=[0.1, 0.2, 0.3],
                metric_type="INVALID_METRIC",
                hybrid_search=False,
            )

    def test_generate_schema_request_valid(self):
        request = GenerateSchemaRequest(
            tenant_code="test_tenant",
            model_name="test_model",
            dimension=384,
            metric_type="COSINE",
            index_type="IVF_FLAT",
        )

        assert request.dimension == 384
        assert request.metric_type == "COSINE"
        assert request.index_type == "IVF_FLAT"

    def test_generate_schema_request_invalid_dimension(self):
        with pytest.raises(ValidationError):
            GenerateSchemaRequest(
                tenant_code="test_tenant",
                model_name="test_model",
                dimension=5000,  # Too large
                metric_type="COSINE",
                index_type="IVF_FLAT",
            )

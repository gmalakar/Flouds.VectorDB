# =============================================================================
# File: test_vector_store_service.py
# Date: 2025-06-14
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

from unittest.mock import patch

import pytest

from app.models.base_request import BaseRequest
from app.models.embeded_meta import EmbeddedMeta
from app.models.embeded_vectors import EmbeddedVectors
from app.models.insert_request import InsertEmbeddedRequest
from app.models.list_response import ListResponse
from app.models.search_request import SearchEmbeddedRequest
from app.models.set_vector_store_request import SetVectorStoreRequest
from app.services.vector_store_service import VectorStoreService


@pytest.fixture
def base_request():
    return BaseRequest(tenant_code="tenant1", token="user:pass")


@pytest.fixture
def set_vector_store_request():
    return SetVectorStoreRequest(
        tenant_code="tenant1", token="user:pass", vector_dimension=256
    )


@pytest.fixture
def insert_embedded_request():
    vec = EmbeddedVectors(chunk="abc", model="test", vector=[0.1, 0.2, 0.3])
    return InsertEmbeddedRequest(tenant_code="tenant1", token="user:pass", data=[vec])


@pytest.fixture
def search_request():
    return SearchEmbeddedRequest(
        tenant_code="tenant1",
        token="user:pass",
        model="test-model",
        limit=10,
        offset=0,
        nprobe=10,
        round_decimal=2,
        score_threshold=0.8,
        metric_type="COSINE",
        vector=[0.1, 0.2, 0.3],
    )


def test_set_user_success(base_request):
    with patch(
        "app.services.vector_store_service.MilvusHelper.set_user"
    ) as mock_set_user:
        mock_set_user.return_value = {"message": "User created"}
        resp = VectorStoreService.set_user(base_request, token="user:pass")
        mock_set_user.assert_called_once_with(tenant_code="tenant1", token="user:pass")
        assert resp.success is True
        assert resp.message == "User created"
        assert resp.for_tenant == "tenant1"
        assert isinstance(resp.time_taken, float)
        assert isinstance(resp.results, dict)


def test_set_user_failure(base_request):
    with patch(
        "app.services.vector_store_service.MilvusHelper.set_user",
        side_effect=Exception("fail"),
    ):
        resp = VectorStoreService.set_user(base_request, token="user:pass")
        assert resp.success is False
        assert "fail" in resp.message
        assert resp.for_tenant == "tenant1"
        assert resp.results == {}


def test_set_vector_store_success(set_vector_store_request):
    with patch(
        "app.services.vector_store_service.MilvusHelper.set_vector_store"
    ) as mock_set_vector_store:
        mock_set_vector_store.return_value = {"result": "ok"}
        resp = VectorStoreService.set_vector_store(set_vector_store_request, token="user:pass")
        assert resp.success is True
        assert resp.results == {"result": "ok"}
        assert resp.for_tenant == "tenant1"


def test_set_vector_store_failure(set_vector_store_request):
    with patch(
        "app.services.vector_store_service.MilvusHelper.set_vector_store",
        side_effect=Exception("fail"),
    ):
        resp = VectorStoreService.set_vector_store(set_vector_store_request, token="user:pass")
        assert resp.success is False
        assert "fail" in resp.message
        assert resp.for_tenant == "tenant1"
        assert resp.results == {}


def test_insert_into_vector_store_success(insert_embedded_request):
    with patch(
        "app.services.vector_store_service.MilvusHelper.insert_embedded_data"
    ) as mock_insert:
        mock_insert.return_value = 1
        resp = VectorStoreService.insert_into_vector_store(insert_embedded_request, token="user:pass")
        assert resp.success is True
        assert "1 vectors inserted" in resp.message
        assert resp.for_tenant == "tenant1"


def test_insert_into_vector_store_failure(insert_embedded_request):
    with patch(
        "app.services.vector_store_service.MilvusHelper.insert_embedded_data",
        side_effect=Exception("fail"),
    ):
        resp = VectorStoreService.insert_into_vector_store(insert_embedded_request, token="user:pass")
        assert resp.success is False
        assert "fail" in resp.message
        assert resp.for_tenant == "tenant1"


def test_list_response_default_values(base_request):
    response: ListResponse = ListResponse(
        for_tenant=base_request.tenant_code,
        success=True,
        message="User set successfully.",
        results={},
        time_taken=0.0,
    )
    assert response.for_tenant == "tenant1"
    assert response.success is True
    assert response.message == "User set successfully."
    assert response.results == {}
    assert response.time_taken == 0.0


def test_list_response_error_handling(base_request):
    response: ListResponse = ListResponse(
        for_tenant=base_request.tenant_code,
        success=False,
        message="",
        results={},
        time_taken=0.0,
    )
    try:
        raise ValueError("An error occurred")
    except Exception as e:
        response.success = False
        response.message = f"Error setting user: {str(e)}"
        response.results = {}

    assert response.for_tenant == "tenant1"
    assert response.success is False
    assert response.message == "Error setting user: An error occurred"
    assert response.results == {}


def test_search_in_vector_store_success(search_request):
    fake_results = [
        EmbeddedMeta(content="chunk1", meta={"score": 0.9}),
        EmbeddedMeta(content="chunk2", meta={"score": 0.85}),
    ]
    with patch(
        "app.services.vector_store_service.MilvusHelper.search_embedded_data"
    ) as mock_search:
        mock_search.return_value = fake_results
        resp = VectorStoreService.search_in_vector_store(search_request, token="user:pass")
        mock_search.assert_called_once_with(request=search_request, token="user:pass")
        assert resp.success is True
        assert resp.data == fake_results
        assert resp.message == "Vector store search completed successfully."
        assert resp.for_tenant == "tenant1"


def test_search_in_vector_store_no_results(search_request):
    with patch(
        "app.services.vector_store_service.MilvusHelper.search_embedded_data"
    ) as mock_search:
        mock_search.return_value = []
        resp = VectorStoreService.search_in_vector_store(search_request, token="user:pass")
        assert resp.success is False
        assert resp.data == []
        assert resp.message == "No vectors found in the vector store."
        assert resp.for_tenant == "tenant1"


def test_search_in_vector_store_failure(search_request):
    with patch(
        "app.services.vector_store_service.MilvusHelper.search_embedded_data",
        side_effect=Exception("fail"),
    ):
        resp = VectorStoreService.search_in_vector_store(search_request, token="user:pass")
        assert resp.success is False
        assert "fail" in resp.message
        assert resp.data == []
        assert resp.for_tenant == "tenant1"

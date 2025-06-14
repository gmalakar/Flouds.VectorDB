import pytest
from unittest.mock import patch, MagicMock

from app.services.vector_store_service import VectorStoreService
from app.models.base_request import BaseRequest
from app.models.set_vector_store_request import SetVectorStoreRequest
from app.models.insert_request import InsertEmbeddedRequest
from app.models.embeded_vectors import EmbeddedVectors

@pytest.fixture
def base_request():
    return BaseRequest(for_tenant="tenant1", token="user:pass")

@pytest.fixture
def set_vector_store_request():
    return SetVectorStoreRequest(for_tenant="tenant1", token="user:pass", vector_dimension=256)

@pytest.fixture
def insert_embedded_request():
    vec = EmbeddedVectors(chunk="abc", model="test", vector=[0.1, 0.2, 0.3])
    return InsertEmbeddedRequest(for_tenant="tenant1", token="user:pass", data=[vec])

def test_set_user_success(base_request):
    with patch("app.services.vector_store_service.MilvusHelper.set_user") as mock_set_user:
        mock_set_user.return_value = {"message": "User created"}
        resp = VectorStoreService.set_user(base_request)
        assert resp.success
        assert resp.message == "User created"
        assert resp.for_tenant == "tenant1"

def test_set_user_failure(base_request):
    with patch("app.services.vector_store_service.MilvusHelper.set_user", side_effect=Exception("fail")):
        resp = VectorStoreService.set_user(base_request)
        assert not resp.success
        assert "fail" in resp.message

def test_set_vector_store_success(set_vector_store_request):
    with patch("app.services.vector_store_service.MilvusHelper.set_vector_store") as mock_set_vector_store:
        mock_set_vector_store.return_value = {"result": "ok"}
        resp = VectorStoreService.set_vector_store(set_vector_store_request)
        assert resp.success
        assert resp.results == {"result": "ok"}

def test_set_vector_store_failure(set_vector_store_request):
    with patch("app.services.vector_store_service.MilvusHelper.set_vector_store", side_effect=Exception("fail")):
        resp = VectorStoreService.set_vector_store(set_vector_store_request)
        assert not resp.success
        assert "fail" in resp.message

def test_insert_into_vector_store_success(insert_embedded_request):
    with patch("app.services.vector_store_service.MilvusHelper.insert_embedded_data") as mock_insert:
        mock_insert.return_value = 1
        resp = VectorStoreService.insert_into_vector_store(insert_embedded_request)
        assert resp.success
        assert "1 vectors inserted" in resp.message

def test_insert_into_vector_store_failure(insert_embedded_request):
    with patch("app.services.vector_store_service.MilvusHelper.insert_embedded_data", side_effect=Exception("fail")):
        resp = VectorStoreService.insert_into_vector_store(insert_embedded_request)
        assert not resp.success
        assert "fail" in resp.message
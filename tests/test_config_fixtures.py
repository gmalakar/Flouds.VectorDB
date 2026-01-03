# =============================================================================
# File: test_config_fixtures.py
# Date: 2025-08-01
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import os
import sys
from unittest.mock import Mock, patch

import pytest

# Add app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def mock_app_settings():
    """Mock APP_SETTINGS for tests."""
    with patch("app.app_init.APP_SETTINGS") as mock_settings:
        # Configure default mock settings
        mock_settings.server.host = "localhost"
        mock_settings.server.port = 8080
        mock_settings.app.is_production = False
        mock_settings.app.debug = False
        mock_settings.vectordb.endpoint = "localhost"
        mock_settings.vectordb.port = 19530
        mock_settings.vectordb.username = "root"
        mock_settings.vectordb.password = "password"
        mock_settings.vectordb.password_file = None
        mock_settings.vectordb.default_dimension = 384
        mock_settings.vectordb.admin_role_name = "admin"
        mock_settings.logging.folder = "/tmp/logs"
        # Ensure security defaults for tests: disable auth unless a test enables it
        mock_settings.security.enabled = False
        mock_settings.security.clients_db_path = str(
            os.path.join(os.path.dirname(__file__), "test_clients.db")
        )
        mock_settings.security.cors_origins = []
        mock_settings.security.trusted_hosts = []
        yield mock_settings


@pytest.fixture
def mock_milvus_client():
    """Mock MilvusClient for tests."""
    with patch("app.milvus.connection_pool.MilvusClient") as mock_client:
        mock_instance = Mock()
        mock_client.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def sample_vector_data():
    """Sample vector data for tests."""
    return {
        "key": "test_key_1",
        "chunk": "This is a test chunk",
        "model": "test_model",
        "vector": [0.1, 0.2, 0.3, 0.4],
        "metadata": {"source": "test", "type": "sample"},
    }

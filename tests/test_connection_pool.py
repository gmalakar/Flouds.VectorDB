# =============================================================================
# File: test_connection_pool.py
# Date: 2025-08-01
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import time
from unittest.mock import Mock, patch

import pytest

from app.milvus.connection_pool import MilvusConnectionPool


class TestMilvusConnectionPool:

    def setup_method(self):
        self.pool = MilvusConnectionPool(max_connections=2, max_idle_time=1)

    @patch("app.milvus.connection_pool.MilvusClient")
    def test_get_connection_creates_new(self, mock_client):
        mock_instance = Mock()
        mock_client.return_value = mock_instance

        client = self.pool.get_connection("uri", "user", "pass", "db")

        assert client == mock_instance
        mock_client.assert_called_once_with(
            uri="uri", user="user", password="pass", db_name="db"
        )

    @patch("app.milvus.connection_pool.MilvusClient")
    def test_get_connection_reuses_existing(self, mock_client):
        mock_instance = Mock()
        mock_client.return_value = mock_instance

        # First call creates connection
        client1 = self.pool.get_connection("uri", "user", "pass", "db")
        # Second call reuses connection
        client2 = self.pool.get_connection("uri", "user", "pass", "db")

        assert client1 == client2
        mock_client.assert_called_once()

    @patch("app.milvus.connection_pool.MilvusClient")
    def test_connection_expiry(self, mock_client):
        mock_client.return_value = Mock()

        # Create connection
        self.pool.get_connection("uri", "user", "pass", "db")
        assert len(self.pool.connections) == 1

        # Wait for expiry
        time.sleep(1.1)

        # Cleanup expired connections
        self.pool.cleanup_expired()
        assert len(self.pool.connections) == 0

    @patch("app.milvus.connection_pool.MilvusClient")
    def test_max_connections_limit(self, mock_client):
        mock_client.return_value = Mock()

        # Fill pool to max capacity
        self.pool.get_connection("uri1", "user", "pass", "db")
        self.pool.get_connection("uri2", "user", "pass", "db")
        assert len(self.pool.connections) == 2

        # Adding third connection should replace oldest
        self.pool.get_connection("uri3", "user", "pass", "db")
        assert len(self.pool.connections) == 2

    def test_get_stats(self):
        with patch("app.milvus.connection_pool.MilvusClient"):
            self.pool.get_connection("uri", "user", "pass", "db")

            stats = self.pool.get_stats()
            assert stats["active_connections"] == 1
            assert stats["max_connections"] == 2
            assert len(stats["connections"]) == 1

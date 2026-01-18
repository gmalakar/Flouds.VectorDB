# =============================================================================
# File: test_health_service.py
# Date: 2025-08-01
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

from unittest.mock import Mock, patch

import pytest  # noqa: F401

from app.services.health_service import HealthService


class TestHealthService:

    @patch("app.services.health_service.MilvusHelper")
    @patch("app.services.health_service.psutil")
    def test_get_health_status_healthy(self, mock_psutil, mock_milvus):
        # Mock Milvus as healthy
        mock_admin_client = Mock()
        mock_milvus._BaseMilvus__get_internal_admin_client.return_value = mock_admin_client
        mock_milvus.check_connection.return_value = True
        mock_admin_client.list_databases.return_value = ["db1", "db2"]

        # Mock system resources as healthy
        mock_psutil.cpu_percent.return_value = 50.0
        mock_memory = Mock()
        mock_memory.percent = 60.0
        mock_memory.available = 4 * 1024**3  # 4GB
        mock_psutil.virtual_memory.return_value = mock_memory

        mock_disk = Mock()
        mock_disk.percent = 70.0
        mock_disk.free = 100 * 1024**3  # 100GB
        mock_psutil.disk_usage.return_value = mock_disk

        health = HealthService.get_health_status()

        assert health.status == "healthy"
        assert health.components["milvus"] == "healthy"
        assert health.components["system"] == "healthy"
        assert health.details["milvus"]["databases"] == 2

    @patch("app.services.health_service.MilvusHelper")
    @patch("app.services.health_service.psutil")
    def test_get_health_status_unhealthy_milvus(self, mock_psutil, mock_milvus):
        # Mock Milvus as unhealthy
        mock_milvus._BaseMilvus__get_internal_admin_client.side_effect = Exception(
            "Connection failed"
        )

        # Mock system resources as healthy
        mock_psutil.cpu_percent.return_value = 50.0
        mock_memory = Mock()
        mock_memory.percent = 60.0
        mock_memory.available = 4 * 1024**3
        mock_psutil.virtual_memory.return_value = mock_memory

        mock_disk = Mock()
        mock_disk.percent = 70.0
        mock_disk.free = 100 * 1024**3
        mock_psutil.disk_usage.return_value = mock_disk

        health = HealthService.get_health_status()

        assert health.status == "unhealthy"
        assert health.components["milvus"] == "unhealthy"
        assert "error" in health.details["milvus"]

    @patch("app.services.health_service.MilvusHelper")
    @patch("app.services.health_service.psutil")
    def test_get_health_status_degraded_system(self, mock_psutil, mock_milvus):
        # Mock Milvus as healthy
        mock_admin_client = Mock()
        mock_milvus._BaseMilvus__get_internal_admin_client.return_value = mock_admin_client
        mock_milvus.check_connection.return_value = True
        mock_admin_client.list_databases.return_value = ["db1"]

        # Mock system resources as degraded (high CPU)
        mock_psutil.cpu_percent.return_value = 85.0  # High CPU
        mock_memory = Mock()
        mock_memory.percent = 60.0
        mock_memory.available = 4 * 1024**3
        mock_psutil.virtual_memory.return_value = mock_memory

        mock_disk = Mock()
        mock_disk.percent = 70.0
        mock_disk.free = 100 * 1024**3
        mock_psutil.disk_usage.return_value = mock_disk

        health = HealthService.get_health_status()

        assert health.status == "degraded"
        assert health.components["system"] == "degraded"
        assert health.details["system"]["cpu_percent"] == 85.0

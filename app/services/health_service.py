# =============================================================================
# File: health_service.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

from datetime import datetime
from time import time
from typing import Dict

import psutil

from app.app_init import APP_SETTINGS
from app.exceptions.custom_exceptions import MilvusConnectionError
from app.logger import get_logger
from app.milvus.milvus_helper import MilvusHelper
from app.models.health_response import HealthResponse

logger = get_logger("health_service")

# Track service start time
SERVICE_START_TIME = time()


class HealthService:
    """
    Service for health check operations.
    """

    @classmethod
    def get_health_status(cls) -> HealthResponse:
        """
        Performs comprehensive health check and returns status.
        """
        components = {}
        details = {}

        # Check Milvus connection
        milvus_status, milvus_details = cls._check_milvus()
        components["milvus"] = milvus_status
        details["milvus"] = milvus_details

        # Check system resources
        system_status, system_details = cls._check_system_resources()
        components["system"] = system_status
        details["system"] = system_details

        # Check configuration
        config_status, config_details = cls._check_configuration()
        components["configuration"] = config_status
        details["configuration"] = config_details

        # Calculate uptime
        uptime = time() - SERVICE_START_TIME

        # Determine overall status
        overall_status = "healthy"
        if any(status == "unhealthy" for status in components.values()):
            overall_status = "unhealthy"
        elif any(status == "degraded" for status in components.values()):
            overall_status = "degraded"

        return HealthResponse(
            status=overall_status,
            service="Flouds Vector",
            version="1.0.0",
            timestamp=datetime.utcnow(),
            uptime_seconds=uptime,
            components=components,
            details=details,
        )

    @classmethod
    def _check_milvus(cls) -> tuple[str, dict]:
        """
        Check Milvus database connectivity with details.
        """
        details = {
            "endpoint": APP_SETTINGS.vectordb.endpoint,
            "port": APP_SETTINGS.vectordb.port,
        }

        try:
            start_time = time()
            admin_client = MilvusHelper._BaseMilvus__get_internal_admin_client()

            if MilvusHelper.check_connection(admin_client):
                response_time = time() - start_time
                details.update(
                    {
                        "status": "connected",
                        "response_time_ms": round(response_time * 1000, 2),
                        "databases": len(admin_client.list_databases()),
                    }
                )
                return "healthy", details
            else:
                details["status"] = "connection_failed"
                return "unhealthy", details

        except (ConnectionError, TimeoutError) as e:
            details.update({"status": "timeout", "error": str(e)})
            logger.warning(f"Milvus connection failed: {str(e)}")
            return "unhealthy", details
        except MilvusConnectionError as e:
            details.update({"status": "milvus_error", "error": str(e)})
            logger.warning(f"Milvus connection error: {str(e)}")
            return "unhealthy", details
        except (ImportError, AttributeError) as e:
            details.update(
                {"status": "client_error", "error": "Milvus client misconfigured"}
            )
            logger.warning(f"Milvus client configuration error: {str(e)}")
            return "unhealthy", details
        except Exception as e:
            details.update({"status": "error", "error": str(e)})
            logger.warning(f"Milvus health check failed: {str(e)}")
            return "unhealthy", details

    @classmethod
    def _check_system_resources(cls) -> tuple[str, dict]:
        """
        Check system resource usage.
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            details = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "disk_percent": disk.percent,
                "disk_free_gb": round(disk.free / (1024**3), 2),
            }

            # Determine status based on thresholds
            if cpu_percent > 90 or memory.percent > 90 or disk.percent > 90:
                return "unhealthy", details
            elif cpu_percent > 80 or memory.percent > 80 or disk.percent > 80:
                return "degraded", details
            else:
                return "healthy", details

        except (OSError, PermissionError) as e:
            logger.error(f"System resource check failed: {e}")
            return "unhealthy", {"error": "System access denied"}
        except (ImportError, AttributeError) as e:
            logger.error(f"System monitoring module error: {e}")
            return "unhealthy", {"error": "System monitoring unavailable"}
        except Exception as e:
            logger.error(f"Unexpected error checking system resources: {e}")
            return "unhealthy", {"error": str(e)}

    @classmethod
    def _check_configuration(cls) -> tuple[str, dict]:
        """
        Check configuration validity.
        """
        details = {}
        issues = []

        try:
            # Check required settings
            if not APP_SETTINGS.vectordb.endpoint:
                issues.append("Missing vectordb endpoint")
            if not APP_SETTINGS.vectordb.username:
                issues.append("Missing vectordb username")
            if (
                not APP_SETTINGS.vectordb.password
                and not APP_SETTINGS.vectordb.password_file
            ):
                issues.append("Missing vectordb password")

            details.update(
                {
                    "environment": (
                        "Production"
                        if APP_SETTINGS.app.is_production
                        else "Development"
                    ),
                    "debug_mode": APP_SETTINGS.app.debug,
                    "server_host": APP_SETTINGS.server.host,
                    "server_port": APP_SETTINGS.server.port,
                }
            )

            if issues:
                details["issues"] = issues
                return "unhealthy", details
            else:
                return "healthy", details

        except (AttributeError, KeyError) as e:
            logger.error(f"Configuration structure error: {e}")
            return "unhealthy", {"error": "Invalid configuration structure"}
        except (ImportError, ModuleNotFoundError) as e:
            logger.error(f"Configuration module error: {e}")
            return "unhealthy", {"error": "Configuration module unavailable"}
        except Exception as e:
            logger.error(f"Unexpected error checking configuration: {e}")
            return "unhealthy", {"error": str(e)}

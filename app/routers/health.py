# =============================================================================
# File: health.py
# Date: 2025-08-01
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

from fastapi import APIRouter

from app.milvus.connection_pool import milvus_pool
from app.models.health_response import HealthResponse
from app.services.health_service import HealthService

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """
    Comprehensive health check endpoint with detailed status information.

    Returns:
        HealthResponse: Health status and details for all components.
    """
    return HealthService.get_health_status()


@router.get("/health/ready")
def readiness_check() -> dict:
    """
    Kubernetes readiness probe endpoint.

    Returns:
        dict: Readiness status for Kubernetes.
    """
    health = HealthService.get_health_status()
    if health.status == "healthy":
        return {"status": "ready"}
    else:
        return {"status": "not_ready", "reason": health.status}


@router.get("/health/live")
def liveness_check() -> dict:
    """
    Kubernetes liveness probe endpoint.

    Returns:
        dict: Liveness status for Kubernetes.
    """
    return {"status": "alive"}


@router.get("/health/connections")
def connection_pool_stats() -> dict:
    """
    Connection pool statistics endpoint.

    Returns:
        dict: Connection pool statistics.
    """
    return milvus_pool.get_stats()

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
def health_check():
    """
    Comprehensive health check endpoint with detailed status information.
    """
    return HealthService.get_health_status()


@router.get("/health/ready")
def readiness_check():
    """
    Kubernetes readiness probe endpoint.
    """
    health = HealthService.get_health_status()
    if health.status == "healthy":
        return {"status": "ready"}
    else:
        return {"status": "not_ready", "reason": health.status}


@router.get("/health/live")
def liveness_check():
    """
    Kubernetes liveness probe endpoint.
    """
    return {"status": "alive"}


@router.get("/health/connections")
def connection_pool_stats():
    """
    Connection pool statistics endpoint.
    """
    return milvus_pool.get_stats()

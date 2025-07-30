# =============================================================================
# File: metrics.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

from fastapi import APIRouter

from app.logger import get_logger

router = APIRouter()
logger = get_logger("metrics_router")


@router.get("/metrics")
def get_metrics():
    """Get basic system metrics"""
    return {"status": "healthy", "service": "FloudsVector.Py", "version": "1.0.0"}

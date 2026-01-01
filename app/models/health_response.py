# =============================================================================
# File: health_response.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """
    Response model for the health check endpoint.

    Attributes:
        status (str): Overall health status: healthy, degraded, or unhealthy.
        service (str): Service name.
        version (str): Service version.
        timestamp (datetime): Health check timestamp.
        uptime_seconds (float): Service uptime in seconds.
        components (Dict[str, str]): Status of individual components.
        details (Optional[Dict[str, dict]]): Additional health check details.
    """

    status: str = Field(
        description="Overall health status: healthy, degraded, or unhealthy"
    )

    service: str = Field(description="Service name")

    version: str = Field(description="Service version")

    timestamp: datetime = Field(description="Health check timestamp")

    uptime_seconds: float = Field(description="Service uptime in seconds")

    components: Dict[str, str] = Field(description="Status of individual components")

    details: Optional[Dict[str, dict]] = Field(
        default=None, description="Additional health check details"
    )

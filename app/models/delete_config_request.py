# =============================================================================
# File: delete_config_request.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

from pydantic import Field

from app.models.base_request import BaseRequest


class DeleteConfigRequest(BaseRequest):
    """Request model for deleting a config entry.

    Fields:
      - key: config key (required)
      - tenant_code: optional tenant code (empty string for default tenant)
    """

    key: str = Field(..., description="The config key.")

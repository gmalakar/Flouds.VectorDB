# =============================================================================
# File: embedding_response.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================


from typing import Any, Dict

from pydantic import Field

from app.models.base_response import BaseResponse


class ListResponse(BaseResponse):
    """
    Response model for list information.

    Attributes:
        results (dict): The dictionary containing the list of items.
    """

    results: Dict[str, Any] = Field(..., description="The dictionary containing the list of items.")

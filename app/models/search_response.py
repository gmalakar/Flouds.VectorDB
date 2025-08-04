# =============================================================================
# File: embedding_response.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

from typing import List

from pydantic import Field

from app.models.base_response import BaseResponse
from app.models.embedded_meta import EmbeddedMeta
from app.models.search_base import SearchEmbeddedBase


class SearchEmbeddedResponse(BaseResponse, SearchEmbeddedBase):
    """
    Response model for text embedding search.
    """

    data: List[EmbeddedMeta] = Field(
        ..., description="The list of embedded vectors returned from the search."
    )

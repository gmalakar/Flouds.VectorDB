# =============================================================================
# File: embedding_response.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

from typing import List

from pydantic import Field

from app.models.base_response import BaseResponse

# from app.models.milvus_db_info import MilvusDBInfo


class ListResponse(BaseResponse):
    """
    Response model for list information.
    """

    results: dict = Field(
        ..., description="The dictionary containing the list of items."
    )

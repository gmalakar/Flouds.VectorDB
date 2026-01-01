# =============================================================================
# File: base_request.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

from pydantic import Field

from app.models.base_request import BaseRequest


class SetUserRequest(BaseRequest):
    """
    Request model for setting a user in the vector store.

    Attributes:
        reset_user (bool): Indicates whether to reset the user.
    """

    reset_user: bool = Field(
        False,
        description="Indicates whether to reset the user. This field is required.",
    )

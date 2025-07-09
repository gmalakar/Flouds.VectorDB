# =============================================================================
# File: reset_password_request.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

from pydantic import BaseModel, Field

from app.models.base_request import BaseRequest


class ResetPasswordRequest(BaseRequest):
    """
    Request model for resetting a user's password in the vector store.
    """

    user_name: str = Field(
        ..., description="The username of the user whose password is to be reset."
    )
    old_password: str = Field(
        ..., description="The old password of the user to be reset."
    )
    new_password: str = Field(..., description="The new password for the user.")

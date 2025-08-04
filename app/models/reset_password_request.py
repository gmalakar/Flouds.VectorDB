# =============================================================================
# File: reset_password_request.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

from pydantic import BaseModel, Field, field_validator

from app.models.base_request import BaseRequest
from app.utils.input_validator import validate_user_id


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

    @field_validator("user_name")
    @classmethod
    def validate_user_name_field(cls, v):
        return validate_user_id(v)

    @field_validator("old_password", "new_password")
    @classmethod
    def validate_password_fields(cls, v):
        if not v or len(v.strip()) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if len(v) > 128:
            raise ValueError("Password too long (max 128 characters)")
        return v

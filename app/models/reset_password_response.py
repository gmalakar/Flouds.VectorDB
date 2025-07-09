# =============================================================================
# File: reset_password_response.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================


from pydantic import Field

from app.models.base_response import BaseResponse


class ResetPasswordResponse(BaseResponse):
    """
    Response model for password reset.
    """

    user_name: str = Field(
        None,
        description="The username of the user requesting the password reset. This field is required.",
    )

    root_user: bool = Field(
        True,
        description="Indicates whether the user is a root user. Default is False.",
    )

    reset_flag: bool = Field(
        False,
        description="Indicates whether the password reset was successful. Default is False.",
    )

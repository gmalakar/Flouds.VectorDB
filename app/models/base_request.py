# =============================================================================
# File: base_request.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.requests import Request

from app.utils.input_validator import validate_tenant_code


class BaseRequest(BaseModel):
    """
    Base request model for Milvus database operations.

    Attributes:
        tenant_code (str): The tenant for which the request is made.
    """

    tenant_code: Optional[str] = Field(
        None,
        description="The tenant for which the request is made. If omitted, it will be resolved from the incoming request headers.",
    )

    model_config = ConfigDict(extra="allow")

    @field_validator("tenant_code")
    @classmethod
    def validate_tenant_code_field(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate the tenant_code field using the custom validator.

        If tenant_code is None at model creation time, leave it as None and allow
        resolution from the request (see `resolve_tenant`).
        """
        if v is None:
            return None
        return validate_tenant_code(v)

    def resolve_tenant(self, request: Request) -> str:
        """Resolve tenant code for this request model.

        If `tenant_code` was provided in the body it is validated and returned.
        Otherwise this method will attempt to read `X-Tenant-Code` from
        `request.headers`, falling back to `request.state.tenant_code` if set by
        authentication middleware. The resolved value is validated, assigned to
        `self.tenant_code`, and returned.

        Raises:
            ValueError: if no tenant code is available or validation fails.
        """
        if self.tenant_code:
            return self.tenant_code

        header = request.headers.get("X-Tenant-Code")
        if not header:
            # Some middleware (AuthMiddleware) may have populated request.state
            header = getattr(request.state, "tenant_code", None)

        if not header:
            raise ValueError("Missing tenant code in request headers")

        validated = validate_tenant_code(header)
        self.tenant_code = validated
        return validated

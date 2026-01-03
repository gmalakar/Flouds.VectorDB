# =============================================================================
# File: validation.py
# Date: 2025-08-01
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.logger import get_logger
from app.utils.log_sanitizer import sanitize_for_log

logger = get_logger("validation_middleware")


class ValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for validating request size and content type.

    Enforces maximum request size and ensures JSON content type for POST/PUT/PATCH.
    """

    async def dispatch(self, request: Request, call_next) -> object:
        """
        Intercept requests to validate size and content type.

        Args:
            request (Request): The incoming HTTP request.
            call_next (Callable): The next middleware or route handler.

        Returns:
            Response: The HTTP response, or raises HTTPException if validation fails.
        """
        # Validate request size
        if hasattr(request, "headers") and "content-length" in request.headers:
            content_length = int(request.headers.get("content-length", 0))
            if content_length > 10 * 1024 * 1024:  # 10MB limit
                client = getattr(request, "client", None)
                client_host = client.host if client is not None else ""
                logger.warning(
                    f"Request too large: {content_length} bytes from {sanitize_for_log(client_host)}"
                )
                raise HTTPException(status_code=413, detail="Request entity too large")

        # Validate content type for POST/PUT requests
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            if not content_type.startswith("application/json"):
                logger.warning(
                    f"Invalid content type: {sanitize_for_log(content_type)}"
                )
                raise HTTPException(status_code=415, detail="Unsupported media type")

        response = await call_next(request)
        return response

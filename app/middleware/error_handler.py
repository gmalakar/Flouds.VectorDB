# =============================================================================
# File: error_handler.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import uuid

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.exceptions.custom_exceptions import FloudsVectorError
from app.logger import get_logger
from app.utils.error_formatter import format_error_response, sanitize_error_message

logger = get_logger("error_handler")


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Middleware for handling and formatting errors in FastAPI applications.

    Catches and processes exceptions, returning standardized JSON error responses.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Intercept requests and handle exceptions, returning formatted JSON error responses.

        Args:
            request (Request): The incoming HTTP request.
            call_next (Callable): The next middleware or route handler.

        Returns:
            JSONResponse: The HTTP response, either from the route or as a formatted error.
        """
        request_id = (
            getattr(request.state, "request_id", None)
            or request.headers.get("X-Request-ID")
            or str(uuid.uuid4())
        )
        request.state.request_id = request_id

        try:
            response = await call_next(request)
            return response
        except HTTPException as e:
            sanitized_error = sanitize_error_message(str(e.detail))
            detail_dict = e.detail if isinstance(e.detail, dict) else None
            # Ensure message is a string for formatting
            if detail_dict and isinstance(detail_dict, dict):
                message = str(detail_dict.get("message") or str(e.detail))
            else:
                message = str(e.detail)
            additional_info = None
            error_type = "HTTP Error"
            if detail_dict:
                error_type = detail_dict.get("error") or error_type
                additional_info = {
                    k: v
                    for k, v in detail_dict.items()
                    if k not in {"error", "message", "type"}
                }
                if detail_dict.get("type"):
                    additional_info["type"] = detail_dict.get("type")

            return JSONResponse(
                status_code=e.status_code,
                headers={"X-Request-ID": request_id},
                content=format_error_response(
                    error_type=error_type,
                    message=message,
                    details=sanitized_error,
                    status_code=e.status_code,
                    request_id=request_id,
                    path=str(request.url.path),
                    method=request.method,
                    additional_info=additional_info,
                ),
            )
        except FloudsVectorError as e:
            sanitized_error = sanitize_error_message(str(e))
            logger.error(f"Application error: {sanitized_error}", exc_info=True)
            return JSONResponse(
                status_code=400,
                headers={"X-Request-ID": request_id},
                content=format_error_response(
                    error_type="Application Error",
                    message="A business logic error occurred",
                    details=str(e),
                    status_code=400,
                    request_id=request_id,
                    path=str(request.url.path),
                    method=request.method,
                ),
            )
        except (ValueError, TypeError) as e:
            sanitized_error = sanitize_error_message(str(e))
            logger.error(f"Validation error: {sanitized_error}", exc_info=True)
            return JSONResponse(
                status_code=400,
                headers={"X-Request-ID": request_id},
                content=format_error_response(
                    error_type="Validation Error",
                    message="Invalid input data provided",
                    details=str(e),
                    status_code=400,
                    request_id=request_id,
                    path=str(request.url.path),
                    method=request.method,
                ),
            )
        except (ConnectionError, TimeoutError) as e:
            sanitized_error = sanitize_error_message(str(e))
            logger.error(f"Connection error: {sanitized_error}", exc_info=True)
            return JSONResponse(
                status_code=503,
                headers={"X-Request-ID": request_id},
                content=format_error_response(
                    error_type="Service Unavailable",
                    message="Unable to connect to required services",
                    details="Connection timeout or failure",
                    status_code=503,
                    retry_after=30,
                    request_id=request_id,
                    path=str(request.url.path),
                    method=request.method,
                ),
            )
        except (PermissionError, OSError) as e:
            sanitized_error = sanitize_error_message(str(e))
            logger.error(f"System error: {sanitized_error}", exc_info=True)
            return JSONResponse(
                status_code=500,
                headers={"X-Request-ID": request_id},
                content=format_error_response(
                    error_type="System Error",
                    message="A system-level error occurred",
                    details="Insufficient permissions or system resource issue",
                    status_code=500,
                    request_id=request_id,
                    path=str(request.url.path),
                    method=request.method,
                ),
            )
        except (ImportError, AttributeError, KeyError) as e:
            sanitized_error = sanitize_error_message(str(e))
            logger.error(f"Configuration error: {sanitized_error}", exc_info=True)
            return JSONResponse(
                status_code=500,
                headers={"X-Request-ID": request_id},
                content=format_error_response(
                    error_type="Configuration Error",
                    message="Service configuration issue detected",
                    details="Service is temporarily misconfigured",
                    status_code=500,
                    request_id=request_id,
                    path=str(request.url.path),
                    method=request.method,
                ),
            )
        except Exception as e:
            sanitized_error = sanitize_error_message(str(e))
            logger.error(f"Unhandled error: {sanitized_error}", exc_info=True)
            return JSONResponse(
                status_code=500,
                headers={"X-Request-ID": request_id},
                content=format_error_response(
                    error_type="Internal Server Error",
                    message="An unexpected error occurred",
                    details="Please try again later or contact support",
                    status_code=500,
                    request_id=request_id,
                    path=str(request.url.path),
                    method=request.method,
                ),
            )

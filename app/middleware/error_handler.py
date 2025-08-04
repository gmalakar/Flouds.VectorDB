# =============================================================================
# File: error_handler.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.exceptions.custom_exceptions import FloudsVectorError
from app.logger import get_logger
from app.utils.error_formatter import format_error_response, sanitize_error_message

logger = get_logger("error_handler")


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except HTTPException:
            raise
        except FloudsVectorError as e:
            sanitized_error = sanitize_error_message(str(e))
            logger.error(f"Application error: {sanitized_error}", exc_info=True)
            return JSONResponse(
                status_code=400,
                content=format_error_response(
                    error_type="Application Error",
                    message="A business logic error occurred",
                    details=str(e),
                    status_code=400,
                ),
            )
        except (ValueError, TypeError) as e:
            sanitized_error = sanitize_error_message(str(e))
            logger.error(f"Validation error: {sanitized_error}", exc_info=True)
            return JSONResponse(
                status_code=400,
                content=format_error_response(
                    error_type="Validation Error",
                    message="Invalid input data provided",
                    details=str(e),
                    status_code=400,
                ),
            )
        except (ConnectionError, TimeoutError) as e:
            sanitized_error = sanitize_error_message(str(e))
            logger.error(f"Connection error: {sanitized_error}", exc_info=True)
            return JSONResponse(
                status_code=503,
                content=format_error_response(
                    error_type="Service Unavailable",
                    message="Unable to connect to required services",
                    details="Connection timeout or failure",
                    status_code=503,
                    retry_after=30,
                ),
            )
        except (PermissionError, OSError) as e:
            sanitized_error = sanitize_error_message(str(e))
            logger.error(f"System error: {sanitized_error}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content=format_error_response(
                    error_type="System Error",
                    message="A system-level error occurred",
                    details="Insufficient permissions or system resource issue",
                    status_code=500,
                ),
            )
        except (ImportError, AttributeError, KeyError) as e:
            sanitized_error = sanitize_error_message(str(e))
            logger.error(f"Configuration error: {sanitized_error}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content=format_error_response(
                    error_type="Configuration Error",
                    message="Service configuration issue detected",
                    details="Service is temporarily misconfigured",
                    status_code=500,
                ),
            )
        except Exception as e:
            sanitized_error = sanitize_error_message(str(e))
            logger.error(f"Unhandled error: {sanitized_error}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content=format_error_response(
                    error_type="Internal Server Error",
                    message="An unexpected error occurred",
                    details="Please try again later or contact support",
                    status_code=500,
                ),
            )

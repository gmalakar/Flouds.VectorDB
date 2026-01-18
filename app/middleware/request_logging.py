# =============================================================================
# File: request_logging.py
# Date: 2025-08-01
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import json
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.logger import get_logger
from app.utils.log_sanitizer import sanitize_for_log

logger = get_logger("request_logging")

# Maximum request body size to log (10KB) to prevent memory exhaustion
MAX_LOG_BODY_SIZE = 10_000


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging incoming requests and outgoing responses.

    Logs request metadata, sanitized request bodies, and response status/duration.
    """

    async def dispatch(self, request: Request, call_next) -> object:
        """
        Intercept requests and log request/response details.

        Args:
            request (Request): The incoming HTTP request.
            call_next (Callable): The next middleware or route handler.

        Returns:
            Response: The HTTP response.
        """
        start_time = time.time()

        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        # Log request
        client_ip = sanitize_for_log(
            request.client.host if request.client else "unknown"
        )
        method = sanitize_for_log(request.method)
        url = sanitize_for_log(str(request.url))
        user_agent = sanitize_for_log(request.headers.get("user-agent", ""))

        logger.info(
            f"Request[{request_id}]: {method} {url} from {client_ip} UA: {user_agent}"
        )

        # Log request body for POST/PUT (sanitized)
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    # Check body size to prevent memory exhaustion
                    body_size = len(body)
                    if body_size > MAX_LOG_BODY_SIZE:
                        logger.debug(
                            f"Request[{request_id}] body: <truncated - {body_size} bytes exceeds limit of {MAX_LOG_BODY_SIZE}>"
                        )
                    else:
                        # Parse and sanitize JSON body
                        try:
                            json_body = json.loads(body)
                            sanitized_body = self._sanitize_request_body(json_body)
                            logger.debug(
                                f"Request[{request_id}] body: {json.dumps(sanitized_body)}"
                            )
                        except json.JSONDecodeError:
                            logger.debug(
                                f"Request[{request_id}] body (non-JSON): {sanitize_for_log(body.decode()[:500])}"
                            )

                # Recreate request with body for downstream processing
                async def receive():
                    return {"type": "http.request", "body": body}

                request._receive = receive
            except Exception as e:
                logger.warning(f"Failed to log request body: {e}")

        response = await call_next(request)

        # Attach request id to response for client tracing
        response.headers["X-Request-ID"] = request_id

        # Log response
        duration = time.time() - start_time
        status_code = response.status_code

        logger.info(
            f"Response[{request_id}]: {status_code} for {method} {url} in {duration:.3f}s"
        )

        return response

    def _sanitize_request_body(self, data) -> object:
        """
        Sanitize request body by removing sensitive fields and limiting size.

        Args:
            data: The request body data (dict, list, or other).

        Returns:
            object: Sanitized representation of the request body for logging.
        """
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                key_lower = key.lower()
                if key_lower in ["password", "secret", "token", "key", "auth"]:
                    sanitized[key] = "[REDACTED]"
                elif key == "vector" and isinstance(value, list):
                    # Truncate large vectors for logging
                    sanitized[key] = f"[vector with {len(value)} dimensions]"
                elif key == "data" and isinstance(value, list):
                    # Limit data array logging
                    sanitized[key] = f"[array with {len(value)} items]"
                else:
                    sanitized[key] = sanitize_for_log(str(value))
            return sanitized
        elif isinstance(data, list):
            return f"[array with {len(data)} items]"
        else:
            return sanitize_for_log(str(data))

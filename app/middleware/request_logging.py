# =============================================================================
# File: request_logging.py
# Date: 2025-08-01
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import json
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.logger import get_logger
from app.utils.input_validator import sanitize_for_log

logger = get_logger("request_logging")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Log request
        client_ip = sanitize_for_log(
            request.client.host if request.client else "unknown"
        )
        method = sanitize_for_log(request.method)
        url = sanitize_for_log(str(request.url))
        user_agent = sanitize_for_log(request.headers.get("user-agent", ""))

        logger.info(f"Request: {method} {url} from {client_ip} UA: {user_agent}")

        # Log request body for POST/PUT (sanitized)
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    # Parse and sanitize JSON body
                    try:
                        json_body = json.loads(body)
                        sanitized_body = self._sanitize_request_body(json_body)
                        logger.debug(f"Request body: {json.dumps(sanitized_body)}")
                    except json.JSONDecodeError:
                        logger.debug(
                            f"Request body (non-JSON): {sanitize_for_log(body.decode()[:500])}"
                        )

                # Recreate request with body for downstream processing
                async def receive():
                    return {"type": "http.request", "body": body}

                request._receive = receive
            except Exception as e:
                logger.warning(f"Failed to log request body: {e}")

        response = await call_next(request)

        # Log response
        duration = time.time() - start_time
        status_code = response.status_code

        logger.info(f"Response: {status_code} for {method} {url} in {duration:.3f}s")

        return response

    def _sanitize_request_body(self, data):
        """Sanitize request body by removing sensitive fields and limiting size"""
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

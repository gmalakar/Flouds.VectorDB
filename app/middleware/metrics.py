# =============================================================================
# File: metrics.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import time
from collections import defaultdict, deque
from typing import Any, Callable, DefaultDict, Deque

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.logger import get_logger
from app.utils.log_sanitizer import sanitize_for_log

logger = get_logger("metrics")


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware for collecting and logging request metrics in FastAPI applications.

    Tracks request counts, processing times, and logs slow requests.
    """

    def __init__(self, app: Any, max_samples: int = 1000, max_endpoints: int = 100):
        """
        Initialize the MetricsMiddleware.

        Args:
            app: The FastAPI application instance.
            max_samples (int, optional): Maximum samples to keep per endpoint. Defaults to 1000.
            max_endpoints (int, optional): Maximum number of endpoints to track. Defaults to 100.
        """
        super().__init__(app)
        self.max_samples = max_samples
        self.max_endpoints = max_endpoints
        self.request_count: DefaultDict[str, int] = defaultdict(int)
        self.request_times: DefaultDict[str, Deque[float]] = defaultdict(
            lambda: deque(maxlen=self.max_samples)
        )

    def _cleanup_old_endpoints(self) -> None:
        """Remove least-recently used endpoints until we are under the limit."""
        try:
            # Determine endpoints with the smallest sample count and remove them first
            while len(self.request_count) > self.max_endpoints:
                # choose endpoint with smallest number of samples
                victim = min(self.request_times.keys(), key=lambda k: len(self.request_times[k]))
                del self.request_times[victim]
                del self.request_count[victim]
        except Exception:
            logger.debug("Failed to cleanup old endpoints in metrics middleware")

    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]) -> Any:
        """
        Intercept requests to collect metrics and log slow requests.

        Args:
            request (Request): The incoming HTTP request.
            call_next (Callable): The next middleware or route handler.

        Returns:
            Response: The HTTP response, with metrics headers added.
        """
        start_time = time.time()

        response = await call_next(request)

        process_time = time.time() - start_time
        endpoint = f"{request.method} {request.url.path}"

        # Track metrics with bounds
        self.request_count[endpoint] += 1
        self.request_times[endpoint].append(process_time)

        # Prevent unbounded endpoint growth
        if len(self.request_count) > self.max_endpoints:
            self._cleanup_old_endpoints()

        # Log slow requests
        if process_time > 1.0:
            logger.warning(f"Slow request: {sanitize_for_log(endpoint)} took {process_time:.2f}s")

        # Add response headers
        response.headers["X-Process-Time"] = str(process_time)

        return response

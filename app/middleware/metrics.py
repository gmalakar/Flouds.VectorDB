# =============================================================================
# File: metrics.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import time
from collections import defaultdict, deque

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.logger import get_logger
from app.utils.log_sanitizer import sanitize_for_log

logger = get_logger("metrics")


class MetricsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_samples=1000, max_endpoints=100):
        super().__init__(app)
        self.max_samples = max_samples
        self.max_endpoints = max_endpoints
        self.request_count = defaultdict(int)
        self.request_times = defaultdict(lambda: deque(maxlen=self.max_samples))

    async def dispatch(self, request: Request, call_next):
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
            logger.warning(
                f"Slow request: {sanitize_for_log(endpoint)} took {process_time:.2f}s"
            )

        # Add response headers
        response.headers["X-Process-Time"] = str(process_time)

        return response

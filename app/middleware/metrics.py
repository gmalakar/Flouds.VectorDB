# =============================================================================
# File: metrics.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import time
from collections import defaultdict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.logger import get_logger

logger = get_logger("metrics")


class MetricsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.request_count = defaultdict(int)
        self.request_times = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        response = await call_next(request)

        process_time = time.time() - start_time
        endpoint = f"{request.method} {request.url.path}"

        # Track metrics
        self.request_count[endpoint] += 1
        self.request_times[endpoint].append(process_time)

        # Log slow requests
        if process_time > 1.0:
            logger.warning(f"Slow request: {endpoint} took {process_time:.2f}s")

        # Add response headers
        response.headers["X-Process-Time"] = str(process_time)

        return response

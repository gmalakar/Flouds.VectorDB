# =============================================================================
# File: rate_limit.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import json
import time
from collections import defaultdict

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.logger import get_logger
from app.utils.error_formatter import format_rate_limit_response
from app.utils.input_validator import sanitize_for_log

logger = get_logger("rate_limit")


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.clients = defaultdict(list)
        self.tenants = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        now = time.time()

        # Get tenant from request body for API endpoints
        tenant_code = await self._extract_tenant_code(request)

        if tenant_code:
            # Rate limit by tenant
            key = f"tenant:{tenant_code}"
            limit_calls = self.calls * 2  # Higher limit for authenticated tenants
        else:
            # Rate limit by IP for non-tenant requests
            key = f"ip:{request.client.host}"
            limit_calls = self.calls

        # Clean old requests
        self.clients[key] = [
            req_time for req_time in self.clients[key] if now - req_time < self.period
        ]

        # Check rate limit
        if len(self.clients[key]) >= limit_calls:
            remaining_time = self.period - (now - min(self.clients[key]))
            logger.warning(f"Rate limit exceeded for {sanitize_for_log(key)}")
            raise HTTPException(
                status_code=429,
                detail=format_rate_limit_response(
                    limit=limit_calls,
                    period=self.period,
                    retry_after=int(remaining_time) + 1,
                    limit_type="tenant" if tenant_code else "ip",
                ),
            )

        # Add current request
        self.clients[key].append(now)

        response = await call_next(request)
        return response

    async def _extract_tenant_code(self, request: Request) -> str:
        """Extract tenant_code from request body."""
        if request.method in ["POST", "PUT", "PATCH"] and request.url.path.startswith(
            "/api/v1/"
        ):
            try:
                body = await request.body()
                if body:
                    data = json.loads(body)
                    tenant_code = data.get("tenant_code")

                    # Recreate request with body for downstream processing
                    async def receive():
                        return {"type": "http.request", "body": body}

                    request._receive = receive

                    return tenant_code
            except (json.JSONDecodeError, AttributeError):
                pass
        return None

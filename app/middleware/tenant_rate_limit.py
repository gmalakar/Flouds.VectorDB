# =============================================================================
# File: tenant_rate_limit.py
# Date: 2025-08-01
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import time
from collections import defaultdict
from typing import Dict

from fastapi import Depends, HTTPException

from app.dependencies.auth import get_token
from app.logger import get_logger
from app.utils.error_formatter import format_rate_limit_response
from app.utils.input_validator import sanitize_for_log

logger = get_logger("tenant_rate_limit")


class TenantRateLimiter:
    def __init__(self):
        self.tenant_requests: Dict[str, list] = defaultdict(list)
        self.tenant_limits = {
            "default": {"calls": 200, "period": 60},
            "premium": {"calls": 1000, "period": 60},
        }

    def check_tenant_limit(
        self, tenant_code: str, tier: str = "default"
    ) -> tuple[bool, dict]:
        """Check if tenant has exceeded rate limit. Returns (allowed, info)."""
        now = time.time()
        limits = self.tenant_limits.get(tier, self.tenant_limits["default"])

        # Clean old requests
        self.tenant_requests[tenant_code] = [
            req_time
            for req_time in self.tenant_requests[tenant_code]
            if now - req_time < limits["period"]
        ]

        current_count = len(self.tenant_requests[tenant_code])
        info = {
            "limit": limits["calls"],
            "period": limits["period"],
            "current": current_count,
            "remaining": max(0, limits["calls"] - current_count),
            "tier": tier,
        }

        # Check limit
        if current_count >= limits["calls"]:
            oldest_request = (
                min(self.tenant_requests[tenant_code])
                if self.tenant_requests[tenant_code]
                else now
            )
            info["retry_after"] = int(limits["period"] - (now - oldest_request)) + 1
            logger.warning(
                f"Tenant rate limit exceeded: {sanitize_for_log(tenant_code)}"
            )
            return False, info

        # Record request
        self.tenant_requests[tenant_code].append(now)
        return True, info


# Global instance
tenant_limiter = TenantRateLimiter()


def check_tenant_rate_limit(tenant_code: str, tier: str = "default"):
    """Dependency to check tenant rate limits."""
    allowed, info = tenant_limiter.check_tenant_limit(tenant_code, tier)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=format_rate_limit_response(
                limit=info["limit"],
                period=info["period"],
                retry_after=info["retry_after"],
                limit_type="tenant",
                tier=tier,
            ),
        )

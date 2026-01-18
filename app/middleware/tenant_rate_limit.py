# =============================================================================
# File: tenant_rate_limit.py
# Date: 2025-08-01
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import time
from collections import defaultdict
from threading import Lock
from typing import Dict

from fastapi import HTTPException

from app.logger import get_logger
from app.utils.error_formatter import format_rate_limit_response
from app.utils.log_sanitizer import sanitize_for_log

logger = get_logger("tenant_rate_limit")


class TenantRateLimiter:
    """
    Rate limiter for tenants, supporting different tiers and limits.
    Thread-safe with automatic cleanup of inactive tenants.
    """

    def __init__(self):
        """
        Initialize the TenantRateLimiter with default and premium tiers.
        """
        self.tenant_requests: Dict[str, list] = defaultdict(list)
        self.tenant_limits = {
            "default": {"calls": 200, "period": 60},
            "premium": {"calls": 1000, "period": 60},
        }
        self._lock = Lock()

    def check_tenant_limit(self, tenant_code: str, tier: str = "default") -> tuple[bool, dict]:
        """
        Check if tenant has exceeded rate limit using monotonic time for reliability.

        Args:
            tenant_code (str): The tenant code to check.
            tier (str, optional): The tenant tier (default or premium).

        Returns:
            tuple[bool, dict]: (allowed, info) where allowed is True if under limit, info contains details.
        """
        # Use monotonic time for relative measurements (immune to system clock adjustments)
        now = time.monotonic()
        limits = self.tenant_limits.get(tier, self.tenant_limits["default"])

        with self._lock:
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
                logger.warning(f"Tenant rate limit exceeded: {sanitize_for_log(tenant_code)}")
                return False, info

            # Record request
            self.tenant_requests[tenant_code].append(now)
            return True, info

    def cleanup_inactive_tenants(self, max_inactive_seconds: int = 3600) -> int:
        """
        Remove tenants with no activity for max_inactive_seconds.
        Prevents memory leaks from accumulating empty tenant entries.

        Args:
            max_inactive_seconds (int): Maximum seconds before considering tenant inactive. Defaults to 1 hour.

        Returns:
            int: Number of inactive tenant entries removed.
        """
        now = time.monotonic()
        removed_count = 0

        with self._lock:
            # Find tenants with no recent activity
            inactive_tenants = [
                tenant
                for tenant, timestamps in self.tenant_requests.items()
                if not timestamps or (now - max(timestamps) > max_inactive_seconds)
            ]

            # Remove inactive tenants
            for tenant in inactive_tenants:
                del self.tenant_requests[tenant]
                removed_count += 1
                logger.debug(f"Cleaned up inactive tenant: {sanitize_for_log(tenant)}")

        return removed_count


# Global instance
tenant_limiter = TenantRateLimiter()


def check_tenant_rate_limit(tenant_code: str, tier: str = "default") -> None:
    """
    Dependency to check tenant rate limits and raise HTTPException if exceeded.

    Args:
        tenant_code (str): The tenant code to check.
        tier (str, optional): The tenant tier (default or premium).

    Raises:
        HTTPException: If the tenant has exceeded the rate limit.
    """
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

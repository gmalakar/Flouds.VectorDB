# =============================================================================
# File: test_tenant_rate_limit_cleanup.py
# Date: 2026-01-18
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import time

from app.middleware.tenant_rate_limit import TenantRateLimiter


def test_cleanup_inactive_tenants_removes_old_and_empty_entries():
    limiter = TenantRateLimiter()
    now = time.monotonic()

    # simulate activity
    limiter.tenant_requests["active"] = [now - 10]
    limiter.tenant_requests["old"] = [now - 4000]
    limiter.tenant_requests["empty"] = []

    removed = limiter.cleanup_inactive_tenants(max_inactive_seconds=3600)
    assert removed == 2
    assert "active" in limiter.tenant_requests
    assert "old" not in limiter.tenant_requests
    assert "empty" not in limiter.tenant_requests

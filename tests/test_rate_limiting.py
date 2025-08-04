# =============================================================================
# File: test_rate_limiting.py
# Date: 2025-08-01
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app.middleware.tenant_rate_limit import TenantRateLimiter


class TestTenantRateLimiter:

    def setup_method(self):
        self.limiter = TenantRateLimiter()
        self.limiter.tenant_limits = {
            "default": {"calls": 2, "period": 60},
            "premium": {"calls": 5, "period": 60},
        }

    def test_check_tenant_limit_allows_requests(self):
        allowed, info = self.limiter.check_tenant_limit("tenant1")
        assert allowed == True
        allowed, info = self.limiter.check_tenant_limit("tenant1")
        assert allowed == True

    def test_check_tenant_limit_blocks_excess(self):
        # Use up the limit
        self.limiter.check_tenant_limit("tenant1")
        self.limiter.check_tenant_limit("tenant1")

        # Third request should be blocked
        allowed, info = self.limiter.check_tenant_limit("tenant1")
        assert allowed == False

    def test_premium_tier_higher_limit(self):
        # Premium tier allows more requests
        for i in range(5):
            allowed, info = self.limiter.check_tenant_limit("tenant1", "premium")
            assert allowed == True

        # Sixth request should be blocked
        allowed, info = self.limiter.check_tenant_limit("tenant1", "premium")
        assert allowed == False

    def test_different_tenants_separate_limits(self):
        # Each tenant has separate limits
        allowed, info = self.limiter.check_tenant_limit("tenant1")
        assert allowed == True
        allowed, info = self.limiter.check_tenant_limit("tenant2")
        assert allowed == True
        allowed, info = self.limiter.check_tenant_limit("tenant1")
        assert allowed == True
        allowed, info = self.limiter.check_tenant_limit("tenant2")
        assert allowed == True

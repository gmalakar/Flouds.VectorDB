# =============================================================================
# File: test_config_service.py
# Date: 2026-01-18
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import json  # noqa: F401

from app.app_init import APP_SETTINGS
from app.services.config_service import config_service


def _setup_db(tmp_path):
    APP_SETTINGS.security.clients_db_path = str(tmp_path / "clients.db")
    config_service.init_db()


def test_set_get_delete_default_tenant(tmp_path):
    _setup_db(tmp_path)

    # initially empty
    assert config_service.get_cors_origins() == []

    # set and get
    config_service.set_cors_origins(["https://a.example"])
    assert config_service.get_cors_origins() == ["https://a.example"]

    # delete and ensure cache invalidated
    config_service.delete_config("cors_origins", "")
    assert config_service.get_cors_origins() == []


def test_tenant_scoped_cache_and_invalidation(tmp_path):
    _setup_db(tmp_path)

    # set per-tenant values
    config_service.set_cors_origins(["t1a"], tenant_code="t1")
    config_service.set_cors_origins(["t2a"], tenant_code="t2")

    assert config_service.get_cors_origins("t1") == ["t1a"]
    assert config_service.get_cors_origins("t2") == ["t2a"]

    # callers should receive a copy; mutations shouldn't affect cached value
    got = config_service.get_cors_origins("t2")
    got.append("mut")
    assert config_service.get_cors_origins("t2") == ["t2a"]

    # update tenant t1 and ensure cache invalidation
    config_service.set_cors_origins(["t1b"], tenant_code="t1")
    assert config_service.get_cors_origins("t1") == ["t1b"]

    # delete tenant t2
    config_service.delete_config("cors_origins", "t2")
    assert config_service.get_cors_origins("t2") == []


def test_trusted_hosts_cache(tmp_path):
    _setup_db(tmp_path)

    assert config_service.get_trusted_hosts() == []
    config_service.set_trusted_hosts(["host1.local"])
    assert config_service.get_trusted_hosts() == ["host1.local"]
    config_service.delete_config("trusted_hosts", "")
    assert config_service.get_trusted_hosts() == []

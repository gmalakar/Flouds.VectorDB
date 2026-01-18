from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware.tenant_security import TenantCorsMiddleware
from app.services.config_service import config_service
from app.modules.key_manager import key_manager


def create_app():
    app = FastAPI()
    app.add_middleware(TenantCorsMiddleware)

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    return app


def test_same_origin_allowed(monkeypatch):
    # Restrict origins to force same-origin path
    monkeypatch.setattr(
        config_service,
        "get_cors_origins",
        lambda tenant_code="": ["https://notmatching.com"],
        raising=False,
    )
    monkeypatch.setattr(
        config_service,
        "get_trusted_hosts",
        lambda tenant_code="": ["*"],
        raising=False,
    )

    app = create_app()
    client = TestClient(app)

    origin = "http://localhost:8000"
    host = "localhost:8000"

    # Preflight
    resp = client.options(
        "/ping",
        headers={"Origin": origin, "Host": host, "X-Tenant-Code": ""},
    )
    assert resp.status_code == 204
    assert resp.headers.get("Access-Control-Allow-Origin") == origin

    # Actual request
    resp = client.get(
        "/ping",
        headers={"Origin": origin, "Host": host, "X-Tenant-Code": ""},
    )
    assert resp.status_code == 200
    assert resp.headers.get("Access-Control-Allow-Origin") == origin


def test_allowed_origin_passes(monkeypatch):
    monkeypatch.setattr(
        config_service,
        "get_cors_origins",
        lambda tenant_code="": ["https://allowed.com"],
        raising=False,
    )
    monkeypatch.setattr(
        config_service,
        "get_trusted_hosts",
        lambda tenant_code="": ["*"],
        raising=False,
    )

    app = create_app()
    client = TestClient(app)

    origin = "https://allowed.com"
    host = "api.example.com"

    resp = client.get(
        "/ping",
        headers={"Origin": origin, "Host": host, "X-Tenant-Code": ""},
    )
    assert resp.status_code == 200
    assert resp.headers.get("Access-Control-Allow-Origin") == origin


def test_blocked_origin(monkeypatch):
    monkeypatch.setattr(
        config_service,
        "get_cors_origins",
        lambda tenant_code="": ["https://allowed.com"],
        raising=False,
    )
    monkeypatch.setattr(
        config_service,
        "get_trusted_hosts",
        lambda tenant_code="": ["api.example.com"],
        raising=False,
    )

    app = create_app()
    client = TestClient(app)

    origin = "https://bad.com"
    host = "api.example.com"

    resp = client.get(
        "/ping",
        headers={"Origin": origin, "Host": host, "X-Tenant-Code": ""},
    )
    assert resp.status_code == 403


def test_trusted_host_with_authentication_allows(monkeypatch):
    # CORS would block, but host is trusted. With token and any authenticated client, allow.
    monkeypatch.setattr(
        config_service,
        "get_cors_origins",
        lambda tenant_code="": ["https://allowed.com"],
        raising=False,
    )
    monkeypatch.setattr(
        config_service,
        "get_trusted_hosts",
        lambda tenant_code="": ["trusted.com"],
        raising=False,
    )

    class Client:
        client_type = "user"

    monkeypatch.setattr(
        key_manager,
        "authenticate_client",
        lambda token, tenant_code="": Client(),
        raising=False,
    )

    app = create_app()
    client = TestClient(app)

    origin = "https://bad.com"
    host = "trusted.com"

    resp = client.get(
        "/ping",
        headers={
            "Origin": origin,
            "Host": host,
            "X-Tenant-Code": "",
            "Authorization": "Bearer abc",
        },
    )
    assert resp.status_code == 200
    assert resp.headers.get("Access-Control-Allow-Origin") == origin


def test_superadmin_bypass_allows(monkeypatch):
    # CORS blocked and host untrusted, but superadmin can bypass
    monkeypatch.setattr(
        config_service,
        "get_cors_origins",
        lambda tenant_code="": ["https://allowed.com"],
        raising=False,
    )
    monkeypatch.setattr(
        config_service,
        "get_trusted_hosts",
        lambda tenant_code="": ["blocked.com"],
        raising=False,
    )

    class SAClient:
        client_type = "superadmin"

    monkeypatch.setattr(
        key_manager,
        "authenticate_client",
        lambda token, tenant_code="": SAClient(),
        raising=False,
    )

    app = create_app()
    client = TestClient(app)

    origin = "https://bad.com"
    host = "untrusted.com"

    resp = client.get(
        "/ping",
        headers={
            "Origin": origin,
            "Host": host,
            "X-Tenant-Code": "",
            "Authorization": "Bearer abc",
        },
    )
    assert resp.status_code == 200
    assert resp.headers.get("Access-Control-Allow-Origin") == origin

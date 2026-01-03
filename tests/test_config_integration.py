from unittest.mock import Mock, patch

from fastapi import status
from starlette.testclient import TestClient

from app.services import config_service


def test_config_crud_and_header_enforcement(tmp_path, mock_app_settings):
    # Prepare settings for integration test
    mock_app_settings.security.enabled = True
    mock_app_settings.security.clients_db_path = str(tmp_path / "clients.db")

    # Ensure config DB initialized in test path
    config_service.init_db()
    # Allow the TestClient host for tenant t1 so TenantTrustedHostMiddleware permits requests
    config_service.set_trusted_hosts(["testserver"], tenant_code="t1")

    # Create a fake admin client object
    fake_client = Mock()
    fake_client.client_id = "admin1"
    fake_client.client_type = "admin"
    fake_client.tenant_code = "t1"

    # Patch Milvus initialization and key manager behavior
    with (
        patch("app.main.MilvusHelper.initialize", return_value=None),
        patch("app.modules.key_manager.key_manager.load_clients", return_value=None),
        patch(
            "app.modules.key_manager.key_manager.get_all_tokens", return_value=["tok"]
        ),
        patch(
            "app.modules.key_manager.key_manager.authenticate_client",
            return_value=fake_client,
        ),
        patch("app.modules.key_manager.key_manager.is_admin", return_value=True),
    ):
        # Import app after patches so startup doesn't try to connect
        from app.main import app as main_app

        client = TestClient(main_app)

        headers = {
            "X-Tenant-Code": "t1",
            "Authorization": "Bearer goodtoken",
        }

        # Add config (uses header tenant)
        r = client.post(
            "/api/v1/config/add",
            json={"key": "cors_origins", "value": '["https://a.example"]'},
            headers=headers,
        )
        if r.status_code != 200:
            # Provide response content to aid debugging
            raise AssertionError(f"Add config failed: {r.status_code} {r.text}")
        assert r.status_code == 200

        # Get config (explicit tenant param)
        r = client.get(
            "/api/v1/config/get",
            params={"key": "cors_origins", "tenant_code": "t1"},
            headers=headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert (
            body["value"] == '["https://a.example"]'
            or body["value"] == '["https://a.example"]'
        )

        # Update config
        r = client.put(
            "/api/v1/config/update",
            json={
                "key": "cors_origins",
                "tenant_code": "t1",
                "value": '["https://b.example"]',
            },
            headers=headers,
        )
        assert r.status_code == 200

        # Ensure updated value observed
        r = client.get(
            "/api/v1/config/get",
            params={"key": "cors_origins", "tenant_code": "t1"},
            headers=headers,
        )
        assert r.status_code == 200
        assert "b.example" in r.json()["value"]

        # Delete config
        r = client.request(
            "DELETE",
            "/api/v1/config/delete",
            json={"key": "cors_origins", "tenant_code": "t1"},
            headers=headers,
        )
        assert r.status_code == 200

        # Ensure deleted -> 404
        r = client.get(
            "/api/v1/config/get",
            params={"key": "cors_origins", "tenant_code": "t1"},
            headers=headers,
        )
        assert r.status_code == 404

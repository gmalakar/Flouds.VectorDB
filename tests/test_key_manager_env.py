# =============================================================================
# File: test_key_manager_env.py
# Date: 2026-01-18
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import os
import tempfile

import pytest
from cryptography.fernet import Fernet

from app.modules.key_manager import KeyManager


def test_env_key_valid_authenticate(monkeypatch):
    # Provide a valid Fernet key via env and verify add/auth flows
    key = Fernet.generate_key()
    monkeypatch.setenv("FLOUDS_ENCRYPTION_KEY", key.decode())
    with tempfile.TemporaryDirectory() as td:
        db = os.path.join(td, "clients.db")
        km = KeyManager(db_path=db)

        assert km.encryption_key == key

        added = km.add_client("testadmin", "s3cr3t-token", "admin")
        assert added is True

        client = km.authenticate_client("testadmin|s3cr3t-token")
        assert client is not None
        assert client.client_id == "testadmin"
        assert km.is_admin("testadmin")


def test_env_key_invalid_raises(monkeypatch):
    # An invalid env value should raise at initialization
    monkeypatch.setenv("FLOUDS_ENCRYPTION_KEY", "not-a-valid-key!!")
    with tempfile.TemporaryDirectory() as td:
        db = os.path.join(td, "clients.db")
        with pytest.raises(ValueError):
            KeyManager(db_path=db)


def test_fallback_file_key(monkeypatch):
    # If env is not set, KeyManager should create a .encryption_key file
    monkeypatch.delenv("FLOUDS_ENCRYPTION_KEY", raising=False)
    with tempfile.TemporaryDirectory() as td:
        db = os.path.join(td, "clients.db")
        km = KeyManager(db_path=db)

        keyfile = os.path.join(td, ".encryption_key")
        assert os.path.exists(keyfile)

        added = km.add_client("user1", "pw1", "api_user")
        assert added is True

        client = km.authenticate_client("user1|pw1")
        assert client is not None

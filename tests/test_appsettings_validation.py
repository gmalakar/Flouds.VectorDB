# =============================================================================
# File: test_appsettings_validation.py
# Date: 2026-01-18
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import pytest

from app.config.appsettings import AppSettings, VectorDBConfig


def test_appsettings_validate_all_passes_with_defaults():
    settings = AppSettings()
    # Should not raise
    AppSettings.validate_all(settings)


def test_vector_dimension_validator_rejects_non_positive():
    with pytest.raises(ValueError):
        VectorDBConfig(default_dimension=0)


def test_appsettings_validate_all_detects_primary_key_conflict():
    settings = AppSettings()
    settings.vectordb.primary_key = settings.vectordb.vector_field_name
    with pytest.raises(ValueError):
        AppSettings.validate_all(settings)

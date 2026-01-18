# =============================================================================
# File: conftest.py
# Date: 2026-01-18
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

# Minimal conftest to expose fixtures for full-suite pytest runs.
# It re-exports `mock_app_settings` defined in `tests/test_configuration.py`.
from tests.test_configuration import mock_app_settings  # noqa: F401

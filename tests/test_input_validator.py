# =============================================================================
# File: test_input_validator.py
# Date: 2025-08-01
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import pytest

from app.utils.input_validator import (
    validate_file_path,
    validate_model_name,
    validate_tenant_code,
    validate_vector,
    validate_vector_dimension,
)
from app.utils.log_sanitizer import sanitize_for_log


class TestInputValidator:

    def test_validate_tenant_code_valid(self):
        assert validate_tenant_code("test_tenant") == "test_tenant"
        assert validate_tenant_code("TENANT123") == "tenant123"

    def test_validate_tenant_code_invalid(self):
        with pytest.raises(ValueError):
            validate_tenant_code("")
        with pytest.raises(ValueError):
            validate_tenant_code("ab")  # Too short
        with pytest.raises(ValueError):
            validate_tenant_code("tenant-with-dash")

    def test_validate_model_name_valid(self):
        assert validate_model_name("bert-base") == "bert-base"
        assert validate_model_name("MODEL_V1.0") == "model_v1.0"

    def test_validate_model_name_invalid(self):
        with pytest.raises(ValueError):
            validate_model_name("")
        with pytest.raises(ValueError):
            validate_model_name("a" * 101)  # Too long

    def test_validate_vector_dimension_valid(self):
        assert validate_vector_dimension(384) == 384
        assert validate_vector_dimension(1) == 1
        assert validate_vector_dimension(4096) == 4096

    def test_validate_vector_dimension_invalid(self):
        with pytest.raises(ValueError):
            validate_vector_dimension(0)
        with pytest.raises(ValueError):
            validate_vector_dimension(4097)
        with pytest.raises(ValueError):
            validate_vector_dimension("384")

    def test_validate_vector_valid(self):
        vector = [0.1, 0.2, -0.3]
        assert validate_vector(vector) == vector

    def test_validate_vector_invalid(self):
        with pytest.raises(ValueError):
            validate_vector([])  # Empty
        with pytest.raises(ValueError):
            validate_vector([0.1, "invalid"])  # Non-numeric
        with pytest.raises(ValueError):
            validate_vector([1e7])  # Too large

    def test_sanitize_for_log(self):
        assert sanitize_for_log("normal text") == "normal text"
        assert sanitize_for_log("text\nwith\nnewlines") == "text_with_newlines"
        assert sanitize_for_log("a" * 300) == "a" * 197 + "..."
        assert sanitize_for_log(None) == "None"

    def test_validate_file_path_valid(self):
        result = validate_file_path("test.txt")
        assert "test.txt" in result

    def test_validate_file_path_traversal(self):
        with pytest.raises(ValueError):
            validate_file_path("../../../etc/passwd", "/safe/dir")

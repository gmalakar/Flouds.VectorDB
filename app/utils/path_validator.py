# =============================================================================
# File: path_validator.py
# Date: 2025-12-31
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================
import os
import re
from pathlib import Path
from typing import IO, Any, Union

from app.exceptions.custom_exceptions import FloudsVectorError


class ResourceException(FloudsVectorError):
    pass


# Dangerous path patterns
DANGEROUS_PATTERNS = [
    r"\.\.",  # Parent directory traversal
    r"~",  # Home directory
    r"\$",  # Environment variables
    r"%",  # Windows environment variables
    r"\\\\",  # UNC paths
]
COMPILED_PATTERNS = [re.compile(pattern) for pattern in DANGEROUS_PATTERNS]


def validate_safe_path(file_path: Union[str, Path], base_dir: Union[str, Path]) -> str:
    try:
        file_str = str(file_path)
        for pattern in COMPILED_PATTERNS:
            if pattern.search(file_str):
                raise ResourceException(f"Dangerous path pattern detected: {file_str}")
        file_path = Path(file_path).resolve()
        base_dir = Path(base_dir).resolve()
        if not base_dir.exists():
            raise ResourceException(f"Base directory does not exist: {base_dir}")
        try:
            file_path.relative_to(base_dir)
        except ValueError:
            raise ResourceException(f"Path traversal detected: {file_path} is outside {base_dir}")
        if len(str(file_path)) > 4096:
            raise ResourceException("Path too long")
        return str(file_path)
    except OSError as e:
        raise ResourceException(f"Cannot access path: {e}")
    except Exception as e:
        raise ResourceException(f"Path validation failed: {e}")


def safe_open(
    file_path: Union[str, Path], base_dir: Union[str, Path], mode: str = "r", **kwargs: Any
) -> IO[Any]:
    safe_path = validate_safe_path(file_path, base_dir)
    if "w" in mode or "a" in mode or "+" in mode:
        parent_dir = Path(safe_path).parent
        if not parent_dir.exists():
            raise ResourceException(f"Parent directory does not exist: {parent_dir}")
        if not os.access(parent_dir, os.W_OK):
            raise ResourceException(f"No write permission for directory: {parent_dir}")
    try:
        return open(safe_path, mode, **kwargs)
    except OSError as e:
        raise ResourceException(f"Cannot open file {safe_path}: {e}")

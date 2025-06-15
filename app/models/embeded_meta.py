# =============================================================================
# File: embeded_vectors.py
# Date: 2025-06-14
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

from typing import List

from pydantic import BaseModel, Field


class EmbeddedMeta(BaseModel):
    content: str = Field(..., description="The text chunk.")
    meta: dict = Field(..., description="The metadata associated with the embedding.")

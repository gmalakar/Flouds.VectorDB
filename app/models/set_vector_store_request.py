# =============================================================================
# File: embedding_request.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

from app.models.base_request import BaseRequest


class SetVectorStoreRequest(BaseRequest):
    """
    Request model for setting up vector store for a tenant.
    """

# =============================================================================
# File: base_nlp_service.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================
from fastapi import Header, HTTPException, status
from app.logger import get_logger
logger = get_logger("dependencies.auth")

def get_token(authorization: str = Header(...)):  # Use ... to make it required
    if not authorization.startswith("Bearer "):
        logger.error(f"Invalid auth header: {authorization}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth header")
    return authorization.split(" ", 1)[1]
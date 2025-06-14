# =============================================================================
# File: setup.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import os
import sys

from app.app_init import APP_SETTINGS
from app.logger import get_logger
from app.milvus.milvus_helper import MilvusHelper

# Load settings using AppSettingsLoader
logger = get_logger("setup")

# Ensure APP_SETTINGS.app.working_dir is set to an absolute path
if not getattr(APP_SETTINGS.app, "working_dir", None) or not os.path.isabs(
    APP_SETTINGS.app.working_dir
):
    APP_SETTINGS.app.working_dir = os.getcwd()
logger.info(f"Appsettings->Working Directory: {APP_SETTINGS.app.working_dir}")

logger.info(f"Environment: {os.getenv('FLOUDS_API_ENV', 'Production')}")

# # initialize Milvus connection if enabled
# if APP_SETTINGS.vectordb:
#     try:
#         MilvusHelper.initialize()
#         logger.info("Milvus connection initialized successfully.")
#     except Exception as e:
#         logger.error(f"Failed to initialize Milvus connection: {str(e)}")
#         sys.exit("Failed to initialize Milvus connection. Exiting application.")
# else:
#     logger.warning("VectorDB configuration is not set. Skipping Milvus initialization.")
#     sys.exit("VectorDB configuration is not set. Exiting application.")

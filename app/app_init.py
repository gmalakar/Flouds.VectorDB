# =============================================================================
# File: app_init.py
# Date: 2025-06-14
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================
import nltk

from app.config.config_loader import ConfigLoader
from app.logger import get_logger

logger = get_logger("app_init")
APP_SETTINGS = ConfigLoader.get_app_settings()
# NLTK setup
try:
    nltk.data.find("corpora/stopwords")
    logger.info("NLTK stopwords corpus already downloaded.")
except LookupError:
    nltk.download("stopwords")
    logger.info("NLTK stopwords corpus downloaded successfully.")

# Print stopwords count
from nltk.corpus import stopwords

stopwords_count = len(stopwords.words("english"))
logger.info(f"Total English stopwords count: {stopwords_count}")

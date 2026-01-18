# =============================================================================
# File: stopwords_util.py
# Date: 2025-08-01
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import json
import os
from typing import Set

from nltk.corpus import stopwords

from app.logger import get_logger
from app.utils.log_sanitizer import sanitize_for_log

logger = get_logger("stopwords_util")


def get_combined_stopwords() -> Set[str]:
    """
    Get a combined set of stopwords from NLTK and a custom configuration file.

    Returns:
        Set[str]: Combined set of stopwords from NLTK and additional config file.
    """
    # Get NLTK stopwords
    try:
        nltk_stopwords = set(stopwords.words("english"))
        logger.debug(f"Loaded {len(nltk_stopwords)} NLTK stopwords")
    except (ImportError, LookupError) as e:
        logger.warning(f"NLTK not available or data missing: {e}")
        nltk_stopwords = set()
    except Exception as e:
        logger.warning(f"Unexpected error loading NLTK stopwords: {e}")
        nltk_stopwords = set()

    # Load additional stopwords from config file
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "stopwords.json")
    additional_stopwords = set()

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            additional_stopwords = {word.lower() for word in config.get("additional_stopwords", [])}
            logger.debug(f"Loaded {len(additional_stopwords)} additional stopwords")
    except (FileNotFoundError, json.JSONDecodeError, PermissionError) as e:
        logger.warning(f"Error loading additional stopwords file: {e}")
    except Exception as e:
        logger.warning(
            f"Unexpected error loading additional stopwords from {sanitize_for_log(config_path)}: {e}"
        )

    # Combine both sets
    combined_stopwords = nltk_stopwords | additional_stopwords
    logger.info(f"Total combined stopwords: {len(combined_stopwords)}")

    return combined_stopwords


# Cache the stopwords for performance
_cached_stopwords = None


def get_stopwords() -> Set[str]:
    """
    Get cached combined stopwords for performance.

    Returns:
        Set[str]: Cached combined stopwords.
    """
    global _cached_stopwords
    if _cached_stopwords is None:
        _cached_stopwords = get_combined_stopwords()
    return _cached_stopwords

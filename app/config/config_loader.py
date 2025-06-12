# =============================================================================
# File: config_loader.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import json
import os

from app.config.appsettings import AppSettings
from app.logger import get_logger

logger = get_logger("config_loader")


class ConfigLoader:

    @staticmethod
    def get_app_settings() -> AppSettings:
        """
        Loads AppSettings from appsettings.json and environment-specific override in the same folder.
        Performs a deep merge for nested config sections.
        """
        data = ConfigLoader._load_config_data("appsettings.json", True)
        appsettings = AppSettings(**data)
        appsettings.server.port = int(os.getenv("FLOUDS_PORT", appsettings.server.port))
        appsettings.server.host = os.getenv("FLOUDS_HOST", appsettings.server.host)
        appsettings.server.type = os.getenv(
            "FLOUDS_SERVER_TYPE", appsettings.server.type
        )
        appsettings.app.debug = os.getenv("FLOUDS_DEBUG_MODE", "0") == "1"
        return appsettings

    @staticmethod
    def _load_config_data(config_file_name: str, check_env_file: bool = False) -> dict:
        """
        Loads a config file and merges with environment-specific override if present.
        Performs a deep merge for nested config sections.
        """
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_path = os.path.join(base_dir, config_file_name)

        logger.debug(f"Loading config from {base_path}")

        def deep_update(d, u):
            for k, v in u.items():
                if isinstance(v, dict) and isinstance(d.get(k), dict):
                    deep_update(d[k], v)
                else:
                    d[k] = v

        if not os.path.exists(base_path):
            raise FileNotFoundError(f"Config file not found: {base_path}")

        with open(base_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Merge environment-specific config if requested and it exists (deep merge)
        if check_env_file:
            env = os.getenv("FLOUDS_API_ENV", "Production")
            name, ext = os.path.splitext(config_file_name)
            env_path = os.path.join(base_dir, f"{name}.{env.lower()}{ext}")
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as f:
                    env_data = json.load(f)
                deep_update(data, env_data)

        return data


# Example usage:
# settings = ConfigLoader.get_app_settings()

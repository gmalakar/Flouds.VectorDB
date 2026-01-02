# =============================================================================
# File: config_loader.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import json
import os
from typing import Any, Dict

from app.config.appsettings import AppSettings
from app.logger import get_logger
from app.utils.input_validator import validate_file_path

logger = get_logger("config_loader")


class ConfigLoader:
    """
    Loader for application configuration files and environment overrides.
    """

    __appsettings: AppSettings = None

    @staticmethod
    def get_app_settings() -> AppSettings:
        """
        Loads AppSettings from appsettings.json and environment-specific override in the same folder.
        Performs a deep merge for nested config sections.
        Applies environment variable overrides for key settings.

        Returns:
            AppSettings: The loaded application settings object.
        """
        data = ConfigLoader._load_config_data("appsettings.json", True)
        ConfigLoader.__appsettings = AppSettings(**data)

        # Apply environment variable overrides
        env = os.getenv("FLOUDS_API_ENV", "Production").lower()
        ConfigLoader.__appsettings.app.is_production = env == "production"
        ConfigLoader.__appsettings.server.port = int(
            os.getenv("SERVER_PORT", ConfigLoader.__appsettings.server.port)
        )
        ConfigLoader.__appsettings.server.host = os.getenv(
            "SERVER_HOST", ConfigLoader.__appsettings.server.host
        )

        ConfigLoader.__appsettings.app.debug = os.getenv("APP_DEBUG_MODE", "0") == "1"

        # Security settings
        ConfigLoader.__appsettings.security.enabled = (
            os.getenv(
                "FLOUDS_SECURITY_ENABLED",
                str(ConfigLoader.__appsettings.security.enabled),
            ).lower()
            == "true"
        )

        # Clients database path
        ConfigLoader.__appsettings.security.enabled = (
            os.getenv(
                "FLOUDS_CLIENTS_DB",
                str(ConfigLoader.__appsettings.security.enabled),
            ).lower()
            == "true"
        )

        logger.info(f"Loaded app settings for environment: {env}")
        return ConfigLoader.__appsettings

    @staticmethod
    def _load_config_data(
        config_file_name: str, check_env_file: bool = False
    ) -> Dict[str, Any]:
        """
        Loads a config file and merges with environment-specific override if present.
        Performs a deep merge for nested config sections.

        Args:
            config_file_name (str): The base config file name.
            check_env_file (bool, optional): Whether to check for environment-specific override. Defaults to False.

        Returns:
            Dict[str, Any]: The merged configuration data.
        """
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # Validate config file path to prevent path traversal
        try:
            base_path = validate_file_path(
                os.path.join(base_dir, config_file_name), base_dir=base_dir
            )
        except ValueError as e:
            raise ValueError(f"Invalid config file path: {e}")

        logger.debug(f"Loading config from {base_path}")

        def deep_update(d: Dict[str, Any], u: Dict[str, Any]):
            for k, v in u.items():
                if isinstance(v, dict) and isinstance(d.get(k), dict):
                    deep_update(d[k], v)
                else:
                    d[k] = v

        if not os.path.exists(base_path):
            logger.error(f"Config file not found: {base_path}")
            raise FileNotFoundError(f"Config file not found: {base_path}")

        try:
            with open(base_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, PermissionError) as e:
            raise ValueError(f"Failed to load config file {base_path}: {e}")

        # Merge environment-specific config if requested and it exists (deep merge)
        if check_env_file:
            env = os.getenv("FLOUDS_API_ENV", "Production")
            name, ext = os.path.splitext(config_file_name)
            try:
                env_path = validate_file_path(
                    os.path.join(base_dir, f"{name}.{env.lower()}{ext}"),
                    base_dir=base_dir,
                )
                if os.path.exists(env_path):
                    logger.info(f"Loading environment-specific config: {env_path}")
                    with open(env_path, "r", encoding="utf-8") as f:
                        env_data = json.load(f)
                    deep_update(data, env_data)
            except ValueError as e:
                logger.warning(f"Invalid environment config path: {e}")
            except (FileNotFoundError, json.JSONDecodeError, PermissionError) as e:
                logger.debug(f"No environment-specific config found for {env}: {e}")

        return data


# Example usage:
# settings = ConfigLoader.get_app_settings()

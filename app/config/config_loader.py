# =============================================================================
# File: config_loader.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import json
import os
from typing import Any, Dict, Optional

from app.config.appsettings import AppSettings
from app.logger import get_logger
from app.utils.input_validator import validate_file_path

logger = get_logger("config_loader")


class ConfigLoader:
    """
    Loader for application configuration files and environment overrides.
    """

    __appsettings: Optional[AppSettings] = None

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

        # Apply environment variable overrides with correct types and sensible fallbacks
        env = os.getenv("FLOUDS_API_ENV", "Production").lower()
        ConfigLoader.__appsettings.app.is_production = env == "production"

        # Server host/port: support both SERVER_* and FLOUDS_* env names
        server_port = os.getenv("FLOUDS_PORT", os.getenv("SERVER_PORT"))
        if server_port is not None:
            try:
                ConfigLoader.__appsettings.server.port = int(server_port)
            except ValueError:
                logger.warning(
                    f"Invalid SERVER PORT value: {server_port}; using config value"
                )

        server_host = os.getenv("FLOUDS_HOST", os.getenv("SERVER_HOST"))
        if server_host:
            ConfigLoader.__appsettings.server.host = server_host

        # Debug mode: accept '1','true','yes' (case-insensitive)
        debug_val = os.getenv("APP_DEBUG_MODE")
        if debug_val is not None:
            ConfigLoader.__appsettings.app.debug = str(debug_val).lower() in (
                "1",
                "true",
                "yes",
            )

        # Security flag
        sec_enabled = os.getenv("FLOUDS_SECURITY_ENABLED")
        if sec_enabled is not None:
            ConfigLoader.__appsettings.security.enabled = str(sec_enabled).lower() in (
                "1",
                "true",
                "yes",
            )

        # Clients DB path
        clients_db = os.getenv("FLOUDS_CLIENTS_DB")
        if clients_db:
            ConfigLoader.__appsettings.security.clients_db_path = clients_db

        # CORS/trusted-hosts are seeded from env at startup (see app/main.py).
        # DB is the canonical runtime source; environment variables are used
        # only for bootstrapping or emergency override via
        # `FLOUDS_CONFIG_OVERRIDE`.

        # VectorDB settings
        v_container = os.getenv("VECTORDB_CONTAINER_NAME")
        if v_container:
            ConfigLoader.__appsettings.vectordb.container_name = v_container

        v_port = os.getenv("VECTORDB_PORT")
        if v_port is not None:
            try:
                ConfigLoader.__appsettings.vectordb.port = int(v_port)
            except ValueError:
                logger.warning(f"Invalid VECTORDB_PORT: {v_port}; using config value")

        v_user = os.getenv("VECTORDB_USERNAME")
        if v_user is not None:
            ConfigLoader.__appsettings.vectordb.username = v_user

        # Password can come from direct env or a path/filename pointing into the secrets dir
        v_password = os.getenv("VECTORDB_PASSWORD")
        if v_password is not None:
            ConfigLoader.__appsettings.vectordb.password = v_password

        # Password file: only support VECTORDB_PASSWORD_FILE (full path or filename)
        v_pass_file = os.getenv("VECTORDB_PASSWORD_FILE")
        if v_pass_file:
            # If a relative filename was provided, replace only the filename portion of the default path
            if os.path.isabs(v_pass_file):
                ConfigLoader.__appsettings.vectordb.password_file = v_pass_file
            else:
                default_dir = os.path.dirname(
                    ConfigLoader.__appsettings.vectordb.password_file
                )
                ConfigLoader.__appsettings.vectordb.password_file = os.path.join(
                    default_dir, v_pass_file
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

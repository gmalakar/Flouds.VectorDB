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
    def _getenv_first(*names: str) -> Optional[str]:
        for n in names:
            v = os.getenv(n)
            if v is not None:
                return v
        return None

    @staticmethod
    def _parse_bool(val: Optional[str]) -> Optional[bool]:
        if val is None:
            return None
        return str(val).lower() in ("1", "true", "yes")

    @staticmethod
    def _parse_int(val: Optional[str]) -> Optional[int]:
        if val is None:
            return None
        try:
            return int(val)
        except ValueError:
            return None

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

        # Ensure CSP values are taken from the JSON if present. We keep the
        # fields default as None in code and populate them explicitly so that the
        # runtime values come from `appsettings.json` rather than hard-coded
        # defaults in the model.
        try:
            sec_section = data.get("security") if isinstance(data, dict) else None
            if sec_section and isinstance(sec_section, dict):
                for k in ("csp_script_src", "csp_style_src", "csp_img_src", "csp_connect_src"):
                    if k in sec_section:
                        try:
                            setattr(
                                ConfigLoader.__appsettings.security,
                                k,
                                sec_section.get(k),
                            )
                        except Exception:
                            logger.debug(f"Failed to apply security.{k} from appsettings.json")
        except Exception:
            # Fail-safe: don't let CSP mapping break startup; log and continue
            logger.debug("No CSP values applied from appsettings.json")

        # Environment variable overrides for CSP arrays. Support either a
        # JSON array value or a comma-separated string. Recognize both a
        # single-underscore and double-underscore env var naming style.
        try:
            env_map = {
                "csp_script_src": (
                    "FLOUDS_SECURITY_CSP_SCRIPT_SRC",
                    "FLOUDS_SECURITY__CSP_SCRIPT_SRC",
                ),
                "csp_style_src": (
                    "FLOUDS_SECURITY_CSP_STYLE_SRC",
                    "FLOUDS_SECURITY__CSP_STYLE_SRC",
                ),
                "csp_img_src": ("FLOUDS_SECURITY_CSP_IMG_SRC", "FLOUDS_SECURITY__CSP_IMG_SRC"),
                "csp_connect_src": (
                    "FLOUDS_SECURITY_CSP_CONNECT_SRC",
                    "FLOUDS_SECURITY__CSP_CONNECT_SRC",
                ),
                "csp_font_src": (
                    "FLOUDS_SECURITY_CSP_FONT_SRC",
                    "FLOUDS_SECURITY__CSP_FONT_SRC",
                ),
                "csp_worker_src": (
                    "FLOUDS_SECURITY_CSP_WORKER_SRC",
                    "FLOUDS_SECURITY__CSP_WORKER_SRC",
                ),
            }
            for field, names in env_map.items():
                env_val = ConfigLoader._getenv_first(*names)
                if env_val is None:
                    continue
                parsed: Optional[list] = None
                # Try JSON first
                try:
                    maybe = json.loads(env_val)
                    if isinstance(maybe, list):
                        # Normalize items (preserve any intentional quoting such as 'self')
                        parsed = [str(x).strip() for x in maybe if str(x).strip()]
                except Exception:
                    # Fallback: comma-separated list. Accept values like
                    # ["'self'","https://..."] or 'self,https://...'
                    raw = env_val.strip()
                    if raw.startswith("[") and raw.endswith("]"):
                        raw = raw[1:-1]
                    parts = []
                    for p in raw.split(","):
                        s = p.strip()
                        if not s:
                            continue
                        # Preserve surrounding quotes so tokens like 'self' remain quoted
                        parts.append(s)
                    parsed = parts

                # If parsed is an empty list treat it as not set (don't overwrite
                # values from appsettings.json). This prevents empty env vars
                # from wiping JSON-provided CSP values.
                if parsed:
                    try:
                        setattr(ConfigLoader.__appsettings.security, field, parsed)
                        logger.info(f"Applied env override for security.{field}")
                    except Exception:
                        logger.warning(f"Failed to set security.{field} from environment")
                else:
                    logger.debug(f"Skipped empty env override for security.{field}")
        except Exception as e:
            logger.debug(f"Error while applying CSP env overrides: {e}")

        # Apply environment variable overrides with correct types and sensible fallbacks
        env = os.getenv("FLOUDS_API_ENV", "Production").lower()
        ConfigLoader.__appsettings.app.is_production = env == "production"

        # Server host/port: use FLOUDS_* env names exclusively.
        server_port = os.getenv("FLOUDS_PORT")
        if server_port is not None:
            try:
                ConfigLoader.__appsettings.server.port = int(server_port)
            except ValueError:
                logger.warning(f"Invalid FLOUDS_PORT value: {server_port}; using config value")

        server_host = os.getenv("FLOUDS_HOST")
        if server_host:
            ConfigLoader.__appsettings.server.host = server_host

        server_openapi_url = os.getenv("FLOUDS_OPENAPI_URL")
        if server_openapi_url:
            ConfigLoader.__appsettings.server.openapi_url = server_openapi_url

        # Docs assets configuration (can be used by the app to choose CDN or proxy)
        docs_asset_base = os.getenv("FLOUDS_DOCS_ASSET_BASE")
        if docs_asset_base is not None:
            ConfigLoader.__appsettings.server.docs_asset_base = docs_asset_base

        docs_use_proxy = os.getenv("FLOUDS_DOCS_USE_PROXY")
        parsed_docs_use_proxy = ConfigLoader._parse_bool(docs_use_proxy)
        if parsed_docs_use_proxy is not None:
            ConfigLoader.__appsettings.server.docs_use_proxy = parsed_docs_use_proxy

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
                default_dir = os.path.dirname(ConfigLoader.__appsettings.vectordb.password_file)
                ConfigLoader.__appsettings.vectordb.password_file = os.path.join(
                    default_dir, v_pass_file
                )

        logger.info(f"Loaded app settings for environment: {env}")
        return ConfigLoader.__appsettings

    @staticmethod
    def _load_config_data(config_file_name: str, check_env_file: bool = False) -> Dict[str, Any]:
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

        def deep_update(d: Dict[str, Any], u: Dict[str, Any]) -> None:
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

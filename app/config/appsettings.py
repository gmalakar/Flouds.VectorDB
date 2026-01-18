# =============================================================================
# File: appsettings.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================
import os

from pydantic import BaseModel, Field, field_validator


class AppConfig(BaseModel):
    """
    Application configuration settings.
    """

    name: str = Field(default="Flouds PY")
    debug: bool = Field(default=False)
    working_dir: str = Field(default=os.getcwd())
    is_production: bool = Field(default=True)
    default_executor_workers: int = Field(
        default=16,
        description="Max workers for the default thread executor used for blocking I/O offload. Set to 0 to use asyncio default (unbounded).",
    )

    @field_validator("default_executor_workers")
    @classmethod
    def validate_workers(cls, v: int) -> int:
        """Validate executor workers is non-negative."""
        if v < 0:
            raise ValueError("default_executor_workers must be >= 0")
        return v


class ServerConfig(BaseModel):
    """
    Server configuration settings.
    """

    host: str = Field(default="127.0.0.1")
    port: int = Field(default=5001)

    @field_validator("host")
    @classmethod
    def validate_host(cls, v: str) -> str:
        """Validate host is not empty."""
        if not v or not v.strip():
            raise ValueError("Server host cannot be empty")
        return v

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate port is in valid range."""
        if not (1 <= v <= 65535):
            raise ValueError("Port must be between 1 and 65535")
        return v


class IndexParams(BaseModel):
    """
    Index parameters for the vector database.
    """

    nlist: int = Field(
        default=1024,
        description="Number of clusters for IVF index. Adjust based on dataset size.",
    )
    metric_type: str = Field(
        default="COSINE",
        description="Distance metric for the vector database.",
    )
    index_type: str = Field(
        default="IVF_FLAT",
        description="Index type for the vector database.",
    )

    @field_validator("nlist")
    @classmethod
    def validate_nlist(cls, v: int) -> int:
        """Validate nlist is positive."""
        if v <= 0:
            raise ValueError("nlist must be greater than 0")
        return v

    @field_validator("metric_type")
    @classmethod
    def validate_metric_type(cls, v: str) -> str:
        """Validate metric_type is one of the supported types."""
        allowed = {"COSINE", "L2", "IP", "HAMMING", "JACCARD"}
        if v.upper() not in allowed:
            raise ValueError(f"metric_type must be one of {allowed}")
        return v.upper()

    @field_validator("index_type")
    @classmethod
    def validate_index_type(cls, v: str) -> str:
        """Validate index_type is one of the supported types."""
        allowed = {"IVF_FLAT", "IVF_SQ8", "FLAT", "HNSW", "HNSWSQ8"}
        if v.upper() not in allowed:
            raise ValueError(f"index_type must be one of {allowed}")
        return v.upper()


class VectorDBConfig(BaseModel):
    """
    Vector database configuration settings.
    """

    container_name: str = Field(default="localhost")
    port: int = Field(default=19530)
    username: str = Field(default="root")
    password: str = Field(default="")
    password_file: str = Field(default="/app/data/secrets/vectordb_password.txt")
    default_dimension: int = Field(default=384)
    primary_key: str = Field(
        default="flouds_vector_id",
        description="Primary key for the vector database. Must be unique for each vector.",
    )
    primary_key_data_type: str = Field(
        default="VARCHAR",
        description="Data type for the primary key in the vector database.",
    )
    vector_field_name: str = Field(
        default="flouds_vector",
        description="Field name for the vector in the vector database.",
    )
    auto_flush_min_batch: int = Field(
        default=100,
        description="Minimum batch size that triggers auto-flush for inserts. Set to 0 to always flush; negative to disable auto-flush by size.",
    )
    admin_role_name: str = Field(
        default="flouds_admin_role",
        description="Role name for the admin user in the vector database.",
    )
    index_params: IndexParams = Field(default_factory=IndexParams)

    @field_validator("container_name")
    @classmethod
    def validate_container_name(cls, v: str) -> str:
        """Validate container_name is not empty."""
        if not v or not v.strip():
            raise ValueError("container_name cannot be empty")
        return v

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate port is in valid range."""
        if not (1 <= v <= 65535):
            raise ValueError("VectorDB port must be between 1 and 65535")
        return v

    @field_validator("default_dimension")
    @classmethod
    def validate_dimension(cls, v: int) -> int:
        """Validate default_dimension is positive."""
        if v <= 0:
            raise ValueError("default_dimension must be greater than 0")
        return v


class SecurityConfig(BaseModel):
    """
    Security configuration settings.
    """

    enabled: bool = Field(default=False)
    clients_db_path: str = Field(default="/app/data/clients.db")
    cors_origins: list[str] = Field(
        default_factory=lambda: ["*"],
        description="List of allowed CORS origins. Use '*' to allow all.",
    )
    trusted_hosts: list[str] = Field(
        default_factory=lambda: ["*"],
        description="List of trusted hostnames for TrustedHostMiddleware. Use '*' to allow all.",
    )

    @field_validator("cors_origins", "trusted_hosts")
    @classmethod
    def validate_origins_and_hosts(cls, v: list[str]) -> list[str]:
        """Validate CORS origins and trusted hosts are not empty lists when security is enabled."""
        if not v:
            raise ValueError("CORS origins and trusted hosts cannot be empty lists")
        return v


class AppSettings(BaseModel):
    """
    Root application settings object with comprehensive validation.

    Validates all configuration sections and ensures consistency across
    interdependent settings. Use validate() to catch all errors during startup.
    """

    app: AppConfig = Field(default_factory=AppConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    vectordb: VectorDBConfig = Field(default_factory=VectorDBConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)

    @classmethod
    def validate_all(cls, settings: "AppSettings") -> None:
        """
        Comprehensive validation of all settings and cross-field dependencies.

        Call this method during application startup to catch configuration errors
        before they cause runtime failures.

        Args:
            settings: The AppSettings instance to validate.

        Raises:
            ValueError: If any validation fails.
        """
        errors = []

        # Validate that required database fields are present
        if not settings.vectordb.container_name:
            errors.append("vectordb.container_name is required")

        if not settings.vectordb.username:
            errors.append("vectordb.username is required")

        # Validate server configuration
        if settings.server.port <= 0:
            errors.append("server.port must be positive")

        # Validate vector dimension is reasonable
        if settings.vectordb.default_dimension < 1 or settings.vectordb.default_dimension > 4096:
            errors.append("vectordb.default_dimension must be between 1 and 4096")

        # Validate primary key configuration
        if not settings.vectordb.primary_key:
            errors.append("vectordb.primary_key cannot be empty")

        if not settings.vectordb.vector_field_name:
            errors.append("vectordb.vector_field_name cannot be empty")

        # Ensure primary key and vector field are different
        if settings.vectordb.primary_key == settings.vectordb.vector_field_name:
            errors.append("primary_key and vector_field_name must be different")

        if errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")

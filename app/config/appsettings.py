# =============================================================================
# File: appsettings.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================
import os

from pydantic import BaseModel, Field


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


class ServerConfig(BaseModel):
    """
    Server configuration settings.
    """

    host: str = Field(default="0.0.0.0")
    port: int = Field(default=5001)


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


class VectorDBConfig(BaseModel):
    """
    Vector database configuration settings.
    """

    endpoint: str = Field(default="localhost")
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


class SecurityConfig(BaseModel):
    """
    Security configuration settings.
    """

    enabled: bool = Field(default=False)
    clients_db_path: str = Field(default="/app/data/clients.db")


class AppSettings(BaseModel):
    """
    Root application settings object.
    """

    app: AppConfig = Field(default_factory=AppConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    vectordb: VectorDBConfig = Field(default_factory=VectorDBConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)

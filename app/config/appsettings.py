# =============================================================================
# File: appsettings.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================
import os
from typing import Optional

from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    name: str = Field(default="Flouds PY")
    debug: bool = Field(default=False)
    working_dir: str = Field(default=os.getcwd())


class ServerConfig(BaseModel):
    type: str = Field(default="uvicorn")
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=5001)
    reload: bool = Field(default=True)
    workers: int = Field(default=4)


class VectorDBConfig(BaseModel):
    endpoint: str = Field(default="localhost")
    port: int = Field(default=19530)
    username: str = Field(default="admin")
    password: str = Field(default="@Milvus2025Milvus#")
    default_dimension: int = Field(default=256)
    admin_role_name: str = Field(
        default="flouds_admin_role",
        description="Role name for the admin user in the vector database.",
    )


class LoggingConfig(BaseModel):
    folder: str = Field(default="logs")
    app_log_file: str = Field(default="flouds.log")


class AppSettings(BaseModel):
    app: AppConfig = Field(default_factory=AppConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    vectordb: VectorDBConfig = Field(default_factory=VectorDBConfig)

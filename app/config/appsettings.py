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
    is_production: bool = Field(default=True)


class ServerConfig(BaseModel):
    type: str = Field(default="uvicorn")
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=5001)


class VectorDBConfig(BaseModel):
    endpoint: str = Field(default="localhost")
    port: int = Field(default=19530)
    username: str = Field(default="admin")
    password: str = Field(default="@Milvus2025Milvus#")
    password_file: str = Field(default="/app/secrets/password.txt")
    default_dimension: int = Field(default=256)
    primary_key: str = Field(
        default="flouds_vector_id",
        description="Primary key for the vector database. Must be unique for each vector.",
    )
    primary_key_type: str = Field(
        default="VARCHAR",
        description="Data type for the primary key in the vector database.",
    )
    vector_field_name: str = Field(
        default="flouds_vector",
        description="Field name for the vector in the vector database.",
    )
    admin_role_name: str = Field(
        default="flouds_admin_role",
        description="Role name for the admin user in the vector database.",
    )


class AppSettings(BaseModel):
    app: AppConfig = Field(default_factory=AppConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    vectordb: VectorDBConfig = Field(default_factory=VectorDBConfig)

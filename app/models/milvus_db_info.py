from pydantic import BaseModel, Field


class MilvusDBInfo(BaseModel):
    tenant_db: str = Field(..., description="The name of the tenant database.")
    client_id: str = Field(..., description="The client ID for authentication.")
    secret_key: str = Field(..., description="The secret key for authentication.")

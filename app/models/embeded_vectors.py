from typing import List

from pydantic import BaseModel, Field


class EmbeddedVectors(BaseModel):
    content: str = Field(..., description="The text content.")
    model_used: str = Field(..., description="The model used for embedding.")
    vectors: List[float] = Field(..., description="The embedding vector values.")

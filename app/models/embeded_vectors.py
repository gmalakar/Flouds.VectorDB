from typing import List

from pydantic import BaseModel, Field


class EmbeddedVectors(BaseModel):
    chunk: str = Field(..., description="The text chunk.")
    model: str = Field(..., description="The model used for embedding.")
    vector: List[float] = Field(..., description="The embedding vector values.")

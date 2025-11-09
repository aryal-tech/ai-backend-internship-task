from typing import Literal, Optional
from pydantic import BaseModel, Field


ChunkStrategy = Literal["fixed", "semantic"]


class IngestResponse(BaseModel):
    document_id: str
    chunks: int
    chunk_strategy: ChunkStrategy
    embedding_model: str
    vector_collection: str
    used_ocr: bool
    skipped_duplicate: bool = Field(default=False)
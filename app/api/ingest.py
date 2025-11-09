from typing import Optional
import json
from fastapi import APIRouter, Depends, File, Form, UploadFile, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.config import get_settings
from app.schemas.ingest import IngestResponse, ChunkStrategy
from app.repositories.vector_store import VectorStore
from app.utils.embeddings import EmbeddingClient
from app.services.ingestion_service import IngestionService

router = APIRouter(prefix="/ingest", tags=["ingestion"])
_SETTINGS = get_settings()

def provide_vector_store(request: Request) -> VectorStore:
    client = request.app.state.qdrant
    return VectorStore(client=client, collection=_SETTINGS.QDRANT_COLLECTION)

def provide_embedder(request: Request) -> EmbeddingClient:
    # Lazy-create and cache in app.state
    eb = getattr(request.app.state, "embedder", None)
    if eb is not None:
        return eb
    try:
        eb = EmbeddingClient()
    except RuntimeError as e:
        # e.g., OPENAI_API_KEY missing
        raise HTTPException(status_code=500, detail=str(e))
    request.app.state.embedder = eb
    return eb

def get_ingestion_service(
    session: AsyncSession = Depends(get_session),
    vector_store: VectorStore = Depends(provide_vector_store),
    embedder: EmbeddingClient = Depends(provide_embedder),
) -> IngestionService:
    return IngestionService(vector_store=vector_store, embedder=embedder, session=session)

@router.post("", response_model=IngestResponse)
async def ingest_document(
    file: UploadFile = File(...),
    chunk_strategy: ChunkStrategy = Form("semantic"),
    chunk_size: int = Form(500),
    overlap: int = Form(50),
    use_ocr: bool = Form(True),
    metadata: Optional[str] = Form(None),
    service: IngestionService = Depends(get_ingestion_service),
) -> IngestResponse:
    extra = {}
    if metadata:
        try:
            extra = json.loads(metadata)
        except Exception:
            extra = {}
    return await service.ingest(
        file=file,
        chunk_strategy=chunk_strategy,
        chunk_size=chunk_size,
        overlap=overlap,
        use_ocr=use_ocr,
        extra_metadata=extra or None,
    )
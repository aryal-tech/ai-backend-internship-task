from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from app.core.db import get_session
from app.core.config import get_settings
from app.repositories.vector_store import VectorStore
from app.repositories.redis_repo import ChatHistory
from app.utils.embeddings import EmbeddingClient
from app.utils.llm import LLMClient
from app.services.rag_service import RAGService
from app.services.booking_service import BookingService
from app.schemas.chat import ChatRequest, ChatResponse
router = APIRouter(prefix="/chat", tags=["chat"])
_SETTINGS = get_settings()

# Dependency Providers
def provide_vector_store(request: Request) -> VectorStore:
    return VectorStore(client=request.app.state.qdrant, collection=_SETTINGS.QDRANT_COLLECTION)

def provide_embedder() -> EmbeddingClient: return EmbeddingClient()
def provide_llm_client() -> LLMClient: return LLMClient()
def provide_chat_history(request: Request) -> ChatHistory: return ChatHistory(client=request.app.state.redis)
def provide_booking_service(session: AsyncSession = Depends(get_session)) -> BookingService: return BookingService(session=session)

def get_rag_service(
    vs: VectorStore = Depends(provide_vector_store), emb: EmbeddingClient = Depends(provide_embedder),
    hist: ChatHistory = Depends(provide_chat_history), llm: LLMClient = Depends(provide_llm_client),
    book: BookingService = Depends(provide_booking_service),
) -> RAGService:
    return RAGService(vector_store=vs, embedder=emb, chat_history=hist, llm_client=llm, booking_service=book)

# API Endpoint
@router.post("", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest, service: RAGService = Depends(get_rag_service)) -> ChatResponse:
    return await service.chat(user_message=req.message, conversation_id=req.conversation_id, k=req.retrieval_k)
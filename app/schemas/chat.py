from typing import List, Optional
from pydantic import BaseModel
from .booking import BookingResponse

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    retrieval_k: int = 4

class Citation(BaseModel):
    doc_id: str
    filename: Optional[str] = None
    score: float

class ChatResponse(BaseModel):
    answer: str
    conversation_id: str
    citations: List[Citation]
    booking_info: Optional[BookingResponse] = None
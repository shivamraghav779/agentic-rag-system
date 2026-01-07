"""Chat-related Pydantic schemas."""
from datetime import datetime
from typing import List
from pydantic import BaseModel


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    document_id: int
    question: str


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    answer: str
    source_documents: List[dict]


class ChatHistoryResponse(BaseModel):
    """Response model for chat history."""
    id: int
    document_id: int
    question: str
    answer: str
    created_at: datetime

    class Config:
        from_attributes = True


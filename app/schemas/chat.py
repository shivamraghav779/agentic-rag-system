"""Chat-related Pydantic schemas."""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    document_id: int
    question: str
    conversation_id: Optional[int] = None  # Optional: if provided, continue existing conversation


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    answer: str
    source_documents: List[dict]
    conversation_id: int  # Return the conversation ID


class ChatHistoryResponse(BaseModel):
    """Response model for chat history."""
    id: int
    conversation_id: int
    document_id: int
    question: str
    answer: str
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    """Response model for conversation."""
    id: int
    user_id: int
    document_id: int
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationCreate(BaseModel):
    """Request model for creating a conversation."""
    document_id: int
    title: Optional[str] = None


class ConversationUpdate(BaseModel):
    """Request model for updating a conversation."""
    title: Optional[str] = None


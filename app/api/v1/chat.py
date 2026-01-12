"""Chat API routes with rate limiting and history."""
from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.api.deps import get_current_active_user
from app.schemas.chat import (
    ChatRequest, ChatResponse, ChatHistoryResponse,
    ConversationResponse, ConversationCreate, ConversationUpdate
)
from app.services.chat_service import ChatService

router = APIRouter()


@router.post("", response_model=ChatResponse)
async def chat_with_document(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Chat with a specific document using RAG.
    Rate limited based on user's chat_limit.
    """
    chat_service = ChatService(db)
    return await chat_service.chat_with_document(request=request, user=current_user)


@router.get("/history", response_model=List[ChatHistoryResponse])
async def get_chat_history(
    document_id: Optional[int] = Query(None, description="Filter by document ID"),
    conversation_id: Optional[int] = Query(None, description="Filter by conversation ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get chat history for the current user, optionally filtered by document or conversation."""
    chat_service = ChatService(db)
    return await chat_service.get_chat_history(
        user=current_user,
        document_id=document_id,
        conversation_id=conversation_id
    )


@router.get("/history/{chat_id}", response_model=ChatHistoryResponse)
async def get_chat_by_id(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific chat history entry."""
    chat_service = ChatService(db)
    return await chat_service.get_chat_by_id(chat_id=chat_id, user=current_user)


@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation_data: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new conversation for a document."""
    chat_service = ChatService(db)
    return await chat_service.create_conversation(conversation_data=conversation_data, user=current_user)


@router.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations(
    document_id: Optional[int] = Query(None, description="Filter by document ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all conversations for the current user, optionally filtered by document."""
    chat_service = ChatService(db)
    return await chat_service.get_conversations(user=current_user, document_id=document_id)


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation_by_id(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific conversation."""
    chat_service = ChatService(db)
    return await chat_service.get_conversation_by_id(conversation_id=conversation_id, user=current_user)


@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: int,
    conversation_data: ConversationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a conversation (e.g., change title)."""
    chat_service = ChatService(db)
    return await chat_service.update_conversation(
        conversation_id=conversation_id,
        conversation_data=conversation_data,
        user=current_user
    )


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a conversation and all its chat history."""
    chat_service = ChatService(db)
    await chat_service.delete_conversation(conversation_id=conversation_id, user=current_user)
    return None

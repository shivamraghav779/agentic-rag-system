"""Chat API routes with rate limiting and history."""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.document import Document
from app.models.chat_history import ChatHistory
from app.models.user import User
from app.api.deps import get_current_active_user
from app.schemas.chat import ChatRequest, ChatResponse, ChatHistoryResponse
from app.services.rag_chain import RAGChain

router = APIRouter()

# Initialize RAG chain
rag_chain = RAGChain()


def check_rate_limit(user: User, db: Session) -> bool:
    """Check if user has remaining chat requests."""
    # Count chat history for today
    today = datetime.utcnow().date()
    today_chats = db.query(ChatHistory).filter(
        ChatHistory.user_id == user.id,
        ChatHistory.created_at >= datetime.combine(today, datetime.min.time())
    ).count()
    
    return today_chats < user.chat_limit


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
    # Check rate limit
    if not check_rate_limit(current_user, db):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. You have {current_user.chat_limit} chats per day."
        )
    
    # Get document from database (must belong to user)
    document = db.query(Document).filter(
        Document.id == request.document_id,
        Document.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    if not request.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty"
        )
    
    try:
        # Get last 5 chat history entries for this document (conversation context)
        recent_chats = db.query(ChatHistory).filter(
            ChatHistory.user_id == current_user.id,
            ChatHistory.document_id == document.id
        ).order_by(ChatHistory.created_at.desc()).limit(5).all()
        
        # Reverse to get chronological order (oldest first)
        conversation_history = [
            {"question": chat.question, "answer": chat.answer}
            for chat in reversed(recent_chats)
        ]
        
        # Query RAG chain with user's system prompt and conversation history
        result = rag_chain.query(
            document.vector_store_path, 
            request.question,
            system_prompt=current_user.system_prompt,
            conversation_history=conversation_history
        )
        
        # Save chat history
        chat_history = ChatHistory(
            user_id=current_user.id,
            document_id=document.id,
            question=request.question,
            answer=result["answer"]
        )
        db.add(chat_history)
        db.commit()
        
        return ChatResponse(
            answer=result["answer"],
            source_documents=result["source_documents"]
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing chat request: {str(e)}"
        )


@router.get("/history", response_model=List[ChatHistoryResponse])
async def get_chat_history(
    document_id: Optional[int] = Query(None, description="Filter by document ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get chat history for the current user, optionally filtered by document."""
    query = db.query(ChatHistory).filter(ChatHistory.user_id == current_user.id)
    
    if document_id:
        # Verify document belongs to user
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == current_user.id
        ).first()
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        query = query.filter(ChatHistory.document_id == document_id)
    
    chat_history = query.order_by(ChatHistory.created_at.desc()).limit(100).all()
    return chat_history


@router.get("/history/{chat_id}", response_model=ChatHistoryResponse)
async def get_chat_by_id(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific chat history entry."""
    chat = db.query(ChatHistory).filter(
        ChatHistory.id == chat_id,
        ChatHistory.user_id == current_user.id
    ).first()
    
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat history not found"
        )
    
    return chat


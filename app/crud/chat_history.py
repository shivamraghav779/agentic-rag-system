"""CRUD operations for ChatHistory model."""
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.chat_history import ChatHistory
from app.models.user import User


class CRUDChatHistory(CRUDBase[ChatHistory, dict, dict]):
    """CRUD operations for ChatHistory model."""
    
    def get_by_user(
        self,
        db: Session,
        *,
        user_id: int,
        document_id: Optional[int] = None,
        conversation_id: Optional[int] = None,
        limit: int = 100
    ) -> List[ChatHistory]:
        """Get chat history by user ID with optional filtering."""
        query = db.query(self.model).filter(self.model.user_id == user_id)
        
        if conversation_id:
            query = query.filter(self.model.conversation_id == conversation_id)
        elif document_id:
            query = query.filter(self.model.document_id == document_id)
        
        return query.order_by(self.model.created_at.asc()).limit(limit).all()
    
    def get_by_conversation(
        self,
        db: Session,
        *,
        conversation_id: int,
        limit: int = 5
    ) -> List[ChatHistory]:
        """Get recent chat history for a conversation (for context)."""
        return db.query(self.model).filter(
            self.model.conversation_id == conversation_id
        ).order_by(self.model.created_at.desc()).limit(limit).all()
    
    def count_today(self, db: Session, *, user_id: int) -> int:
        """Count chat history entries for today."""
        today = datetime.utcnow().date()
        return db.query(self.model).filter(
            self.model.user_id == user_id,
            self.model.created_at >= datetime.combine(today, datetime.min.time())
        ).count()
    
    def can_access(self, chat_history: ChatHistory, user: User) -> bool:
        """Check if user can access chat history."""
        return chat_history.user_id == user.id


# Create instance
chat_history = CRUDChatHistory(ChatHistory)


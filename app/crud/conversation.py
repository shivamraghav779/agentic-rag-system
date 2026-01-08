"""CRUD operations for Conversation model."""
from typing import Optional, List
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.conversation import Conversation
from app.models.user import User
from app.schemas.chat import ConversationCreate, ConversationUpdate


class CRUDConversation(CRUDBase[Conversation, ConversationCreate, ConversationUpdate]):
    """CRUD operations for Conversation model."""
    
    def get_by_user(
        self,
        db: Session,
        *,
        user_id: int,
        document_id: Optional[int] = None
    ) -> List[Conversation]:
        """Get conversations by user ID, optionally filtered by document."""
        query = db.query(self.model).filter(self.model.user_id == user_id)
        
        if document_id:
            query = query.filter(self.model.document_id == document_id)
        
        return query.order_by(self.model.created_at.desc()).all()
    
    def get_by_user_and_document(
        self,
        db: Session,
        *,
        user_id: int,
        document_id: int,
        conversation_id: int
    ) -> Optional[Conversation]:
        """Get a specific conversation by user, document, and conversation ID."""
        return db.query(self.model).filter(
            self.model.id == conversation_id,
            self.model.user_id == user_id,
            self.model.document_id == document_id
        ).first()
    
    def can_access(self, conversation: Conversation, user: User) -> bool:
        """Check if user can access a conversation."""
        return conversation.user_id == user.id


# Create instance
conversation = CRUDConversation(Conversation)


"""CRUD operations for Conversation model."""
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.conversation import Conversation
from app.models.user import User
from app.schemas.chat import ConversationCreate, ConversationUpdate


class CRUDConversation(CRUDBase[Conversation, ConversationCreate, ConversationUpdate]):
    """CRUD operations for Conversation model."""

    async def get_by_user(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        document_id: Optional[int] = None
    ) -> List[Conversation]:
        """Get conversations by user ID, optionally filtered by document."""
        query = select(Conversation).where(Conversation.user_id == user_id)
        if document_id is not None:
            query = query.where(Conversation.document_id == document_id)
        query = query.order_by(Conversation.created_at.desc())
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_by_user_and_document(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        document_id: int,
        conversation_id: int
    ) -> Optional[Conversation]:
        """Get a specific conversation by user, document, and conversation ID."""
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
                Conversation.document_id == document_id
            )
        )
        return result.scalar_one_or_none()

    def can_access(self, conversation: Conversation, user: User) -> bool:
        """Check if user can access a conversation."""
        return conversation.user_id == user.id


conversation = CRUDConversation(Conversation)

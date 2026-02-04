"""CRUD operations for ChatHistory model."""
from typing import Optional, List
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.chat_history import ChatHistory
from app.models.user import User


class CRUDChatHistory(CRUDBase[ChatHistory, dict, dict]):
    """CRUD operations for ChatHistory model."""

    async def get_by_user(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        document_id: Optional[int] = None,
        conversation_id: Optional[int] = None,
        limit: int = 100
    ) -> List[ChatHistory]:
        """Get chat history by user ID with optional filtering."""
        query = select(ChatHistory).where(ChatHistory.user_id == user_id)
        if conversation_id is not None:
            query = query.where(ChatHistory.conversation_id == conversation_id)
        elif document_id is not None:
            query = query.where(ChatHistory.document_id == document_id)
        query = query.order_by(ChatHistory.created_at.asc()).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_by_conversation(
        self,
        db: AsyncSession,
        *,
        conversation_id: int,
        limit: int = 5
    ) -> List[ChatHistory]:
        """Get recent chat history for a conversation (for context)."""
        result = await db.execute(
            select(ChatHistory)
            .where(ChatHistory.conversation_id == conversation_id)
            .order_by(ChatHistory.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_today(self, db: AsyncSession, *, user_id: int) -> int:
        """Count chat history entries for today."""
        from sqlalchemy import func
        today = datetime.utcnow().date()
        result = await db.execute(
            select(func.count(ChatHistory.id)).where(
                ChatHistory.user_id == user_id,
                ChatHistory.created_at >= datetime.combine(today, datetime.min.time())
            )
        )
        return result.scalar() or 0

    def can_access(self, chat_history: ChatHistory, user: User) -> bool:
        """Check if user can access chat history."""
        return chat_history.user_id == user.id


chat_history = CRUDChatHistory(ChatHistory)

"""Conversation model."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class Conversation(Base):
    """Conversation model for grouping chats."""
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    title = Column(String(500), nullable=True)  # Optional conversation title
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    document = relationship("Document", back_populates="conversations")
    chat_history = relationship("ChatHistory", back_populates="conversation", cascade="all, delete-orphan")


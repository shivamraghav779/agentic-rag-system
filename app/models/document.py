"""Document model."""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class Document(Base):
    """Document metadata model."""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String, nullable=False, index=True)
    file_type = Column(String, nullable=False)  # pdf, docx, txt, html
    file_path = Column(String, nullable=False)
    vector_store_path = Column(String, nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow)
    file_size = Column(Integer)  # Size in bytes
    chunk_count = Column(Integer, default=0)
    extra_metadata = Column(Text)  # JSON string for additional metadata
    
    # Relationships
    owner = relationship("User", back_populates="documents")
    chat_history = relationship("ChatHistory", back_populates="document", cascade="all, delete-orphan")


"""Document category description model."""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class DocumentCategoryDescription(Base):
    """Model for storing descriptions of document categories per organization."""
    __tablename__ = "document_category_descriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)  # Organization-specific category name
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Ensure one description per category per organization
    __table_args__ = (
        UniqueConstraint('organization_id', 'category', name='uq_org_category'),
    )
    
    # Relationships
    organization = relationship("Organization", back_populates="category_descriptions")


"""Document category description schemas."""
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class DocumentCategoryDescriptionBase(BaseModel):
    """Base schema for document category description."""
    category: str = Field(..., min_length=1, max_length=100, description="Organization-specific category name")
    description: Optional[str] = None


class DocumentCategoryDescriptionCreate(DocumentCategoryDescriptionBase):
    """Schema for creating a document category description."""
    pass


class DocumentCategoryDescriptionUpdate(BaseModel):
    """Schema for updating a document category description."""
    description: Optional[str] = None


class DocumentCategoryDescriptionResponse(DocumentCategoryDescriptionBase):
    """Schema for document category description response."""
    id: int
    organization_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


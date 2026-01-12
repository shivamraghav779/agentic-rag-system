"""Document-related Pydantic schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator


class DocumentInfo(BaseModel):
    """Document information model."""
    id: int
    filename: str
    file_type: str
    organization_id: int
    category: Optional[str] = None
    version: int = 1
    upload_date: datetime
    file_size: Optional[int]
    chunk_count: int

    @field_validator('version', mode='before')
    @classmethod
    def set_version_default(cls, v):
        """Convert None to 1 for version field."""
        return v if v is not None else 1

    class Config:
        from_attributes = True


class UploadResponse(BaseModel):
    """Response model for upload endpoint."""
    document_id: int
    filename: str
    message: str
    chunk_count: int


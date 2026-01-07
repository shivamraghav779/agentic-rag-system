"""Document-related Pydantic schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class DocumentInfo(BaseModel):
    """Document information model."""
    id: int
    filename: str
    file_type: str
    upload_date: datetime
    file_size: Optional[int]
    chunk_count: int

    class Config:
        from_attributes = True


class UploadResponse(BaseModel):
    """Response model for upload endpoint."""
    document_id: int
    filename: str
    message: str
    chunk_count: int


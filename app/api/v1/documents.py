"""Document management API routes."""
from typing import List
from fastapi import APIRouter, File, UploadFile, Depends, status, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.models.user import User
from app.api.deps import get_current_active_user
from app.schemas.document import DocumentInfo, UploadResponse
from app.services.document_service import DocumentService

router = APIRouter()


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    organization_id: Optional[int] = Query(None, description="Organization ID (defaults to user's organization)"),
    category: Optional[str] = Query(None, description="Document category (organization-specific)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Upload and process a document.
    
    Supported formats: PDF, DOCX, TXT, HTML
    
    Documents are scoped to organizations. Users can only upload to their organization.
    """
    document_service = DocumentService(db)
    return await document_service.upload_document(
        file=file,
        user=current_user,
        organization_id=organization_id,
        category=category
    )


@router.get("", response_model=List[DocumentInfo])
async def list_documents(
    organization_id: int = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List documents based on user's organization access."""
    document_service = DocumentService(db)
    return document_service.list_documents(
        user=current_user,
        organization_id=organization_id,
        category=category
    )


@router.get("/{document_id}", response_model=DocumentInfo)
async def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get information about a specific document."""
    document_service = DocumentService(db)
    return document_service.get_document(document_id=document_id, user=current_user)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a document and its associated vector store."""
    document_service = DocumentService(db)
    document_service.delete_document(document_id=document_id, user=current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

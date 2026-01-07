"""Document management API routes."""
import os
import uuid
from pathlib import Path
from typing import List
from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.document import Document
from app.models.user import User
from app.api.deps import get_current_active_user
from app.schemas.document import DocumentInfo, UploadResponse
from app.services.document_processor import DocumentProcessor
from app.services.vector_store import VectorStoreManager

router = APIRouter()

# Initialize components
document_processor = DocumentProcessor()
vector_store_manager = VectorStoreManager()


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Upload and process a document.
    
    Supported formats: PDF, DOCX, TXT, HTML
    """
    # Validate file type
    allowed_types = {
        'application/pdf': 'pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
        'text/plain': 'txt',
        'text/html': 'html'
    }
    
    file_type = allowed_types.get(file.content_type)
    if not file_type:
        # Try to infer from extension
        filename_lower = file.filename.lower()
        if filename_lower.endswith('.pdf'):
            file_type = 'pdf'
        elif filename_lower.endswith(('.docx', '.doc')):
            file_type = 'docx'
        elif filename_lower.endswith('.txt'):
            file_type = 'txt'
        elif filename_lower.endswith(('.html', '.htm')):
            file_type = 'html'
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type. Supported: PDF, DOCX, TXT, HTML"
            )
    
    try:
        # Generate unique filename
        file_id = str(uuid.uuid4())
        file_extension = Path(file.filename).suffix
        safe_filename = f"{file_id}{file_extension}"
        file_path = os.path.join(settings.upload_dir, safe_filename)
        
        # Save uploaded file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        file_size = len(content)
        
        # Process document
        documents = document_processor.process_document(file_path, file_type)
        chunk_count = len(documents)
        
        if chunk_count == 0:
            os.remove(file_path)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document could not be processed or is empty"
            )
        
        # Create vector store
        vector_store_name = f"doc_{file_id}"
        vector_store_path = vector_store_manager.create_vector_store(
            documents, vector_store_name
        )
        
        # Save to database
        db_document = Document(
            user_id=current_user.id,
            filename=file.filename,
            file_type=file_type,
            file_path=file_path,
            vector_store_path=vector_store_path,
            file_size=file_size,
            chunk_count=chunk_count
        )
        db.add(db_document)
        db.commit()
        db.refresh(db_document)
        
        return UploadResponse(
            document_id=db_document.id,
            filename=file.filename,
            message="Document uploaded and processed successfully",
            chunk_count=chunk_count
        )
    
    except Exception as e:
        # Clean up on error
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing document: {str(e)}"
        )


@router.get("", response_model=List[DocumentInfo])
async def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all documents for the current user."""
    documents = db.query(Document).filter(
        Document.user_id == current_user.id
    ).order_by(Document.upload_date.desc()).all()
    return documents


@router.get("/{document_id}", response_model=DocumentInfo)
async def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get information about a specific document."""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a document and its associated vector store."""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    try:
        # Delete vector store
        if os.path.exists(document.vector_store_path):
            vector_store_manager.delete_vector_store(document.vector_store_path)
        
        # Delete file
        if os.path.exists(document.file_path):
            os.remove(document.file_path)
        
        # Delete from database
        db.delete(document)
        db.commit()
        
        return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting document: {str(e)}"
        )


"""Document service layer."""
import os
import uuid
from pathlib import Path
from typing import List, Optional
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.crud.document import document as document_crud
from app.crud.organization import organization as organization_crud
from app.models.document import Document
from app.models.user import User, UserRole
from app.schemas.document import UploadResponse
from app.services.document_processor import DocumentProcessor
from app.services.vector_store import VectorStoreManager


class DocumentService:
    """Service for document operations."""
    
    def __init__(self, db: Session):
        """Initialize document service with database session."""
        self.db = db
        self.document_crud = document_crud
        self.organization_crud = organization_crud
        self.document_processor = DocumentProcessor()
        self.vector_store_manager = VectorStoreManager()
    
    def upload_document(
        self,
        file: UploadFile,
        user: User,
        organization_id: Optional[int] = None,
        category: Optional[str] = None
    ) -> UploadResponse:
        """
        Upload and process a document.
        
        Args:
            file: Uploaded file
            user: Current user
            organization_id: Organization ID (defaults to user's organization)
            category: Document category
            
        Returns:
            Upload response with document info
            
        Raises:
            HTTPException: If user cannot upload or processing fails
        """
        # Validate user can upload
        if not user.is_organization_user():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must be assigned to an organization to upload documents. Private users cannot upload documents."
            )
        
        # Determine organization_id
        if organization_id is None:
            organization_id = user.organization_id
        else:
            # Verify user can access this organization
            if not user.can_access_organization(organization_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this organization"
                )
        
        # Verify organization exists
        org = self.organization_crud.get(self.db, id=organization_id)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        # Validate file type
        file_type = self._validate_file_type(file)
        
        try:
            # Generate unique filename
            file_id = str(uuid.uuid4())
            file_extension = Path(file.filename).suffix
            safe_filename = f"{file_id}{file_extension}"
            file_path = os.path.join(settings.upload_dir, safe_filename)

            # Save uploaded file
            content = file.read()
            with open(file_path, "wb") as buffer:
                buffer.write(content)
            
            file_size = len(content)
            
            # Process document
            documents = self.document_processor.process_document(file_path, file_type)
            chunk_count = len(documents)
            
            if chunk_count == 0:
                os.remove(file_path)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Document could not be processed or is empty"
                )
            
            # Create vector store
            vector_store_name = f"doc_{file_id}"
            vector_store_path = self.vector_store_manager.create_vector_store(
                documents, vector_store_name
            )
            
            # Save to database
            document_dict = {
                "user_id": user.id,
                "organization_id": organization_id,
                "filename": file.filename,
                "file_type": file_type,
                "file_path": file_path,
                "vector_store_path": vector_store_path,
                "file_size": file_size,
                "chunk_count": chunk_count,
                "category": category,
                "version": 1
            }
            
            db_document = self.document_crud.create_from_dict(self.db, obj_dict=document_dict)
            
            return UploadResponse(
                document_id=db_document.id,
                filename=file.filename,
                message="Document uploaded and processed successfully",
                chunk_count=chunk_count
            )
        
        except HTTPException:
            raise
        except Exception as e:
            # Clean up on error
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error processing document: {str(e)}"
            )
    
    def list_documents(
        self,
        user: User,
        organization_id: Optional[int] = None,
        category: Optional[str] = None
    ) -> List[Document]:
        """
        List documents accessible by user.
        
        Args:
            user: Current user
            organization_id: Optional organization filter
            category: Optional category filter
            
        Returns:
            List of documents
        """
        # Private users cannot see documents
        if not user.is_organization_user():
            return []
        
        # If organization_id specified, verify access
        if organization_id is not None:
            if not user.can_access_organization(organization_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this organization"
                )
            return self.document_crud.get_by_organization(
                self.db,
                organization_id=organization_id,
                category=category,
                user=user
            )
        
        # Get user's organization documents
        if user.organization_id:
            return self.document_crud.get_by_organization(
                self.db,
                organization_id=user.organization_id,
                category=category,
                user=user
            )
        
        return []
    
    def get_document(self, document_id: int, user: User) -> Document:
        """
        Get a specific document.
        
        Args:
            document_id: Document ID
            user: Current user
            
        Returns:
            Document
            
        Raises:
            HTTPException: If document not found or access denied
        """
        # Private users cannot access documents
        if not user.is_organization_user():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Private users cannot access documents. You must be part of an organization."
            )
        
        document = self.document_crud.get(self.db, id=document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Check access
        if not self.document_crud.can_access(document, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this document"
            )
        
        return document
    
    def delete_document(self, document_id: int, user: User) -> None:
        """
        Delete a document.
        
        Args:
            document_id: Document ID
            user: Current user
            
        Raises:
            HTTPException: If document not found or access denied
        """
        # Private users cannot delete documents
        if not user.is_organization_user():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Private users cannot delete documents. You must be part of an organization."
            )
        
        document = self.document_crud.get(self.db, id=document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Check organization access
        if not self.document_crud.can_access(document, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this document"
            )
        
        # Check delete permissions
        if not self.document_crud.can_delete(document, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to delete this document"
            )
        
        try:
            # Store paths before deletion
            vector_store_path = document.vector_store_path
            file_path = document.file_path
            
            # Delete from database
            self.document_crud.delete(self.db, id=document_id)
            
            # Delete vector store
            try:
                if vector_store_path:
                    self.vector_store_manager.delete_vector_store(vector_store_path)
            except Exception as e:
                print(f"Warning: Could not delete vector store at {vector_store_path}: {str(e)}")
            
            # Delete uploaded file
            try:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"Warning: Could not delete file at {file_path}: {str(e)}")
        
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting document: {str(e)}"
            )
    
    def _validate_file_type(self, file: UploadFile) -> str:
        """
        Validate and determine file type.
        
        Args:
            file: Uploaded file
            
        Returns:
            File type string
            
        Raises:
            HTTPException: If file type is unsupported
        """
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
        
        return file_type


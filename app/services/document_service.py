"""Document service layer."""
import os
import uuid
from pathlib import Path
from typing import List, Optional
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.artifact_paths import (
    get_organization_structured_data_dir,
    get_organization_upload_dir,
    get_organization_vector_store_dir,
)
from app.crud.document import document as document_crud
from app.crud.organization import organization as organization_crud
from app.models.document import Document
from app.models.user import User, UserRole
from app.schemas.document import UploadResponse
from app.services.document_processor import DocumentProcessor
from app.services.vector_store import VectorStoreManager
from app.services.structured_data_processor import process_structured

# File types that use hybrid SQL + RAG pipeline (orchestrator)
STRUCTURED_FILE_TYPES = frozenset({"csv", "xlsx", "xls", "db", "sqlite"})


class DocumentService:
    """Service for document operations."""

    def __init__(self, db: AsyncSession):
        """Initialize document service with database session."""
        self.db = db
        self.document_crud = document_crud
        self.organization_crud = organization_crud
        self.document_processor = DocumentProcessor()
        self.vector_store_manager = VectorStoreManager()
    
    async def upload_document(
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
        org = await self.organization_crud.get(self.db, id=organization_id)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        # Validate file type
        file_type = self._validate_file_type(file)
        
        try:
            file_id = str(uuid.uuid4())
            file_extension = Path(file.filename).suffix
            safe_filename = f"{file_id}{file_extension}"
            # Per-org layout: artifacts/{org_id}/uploads|vector_store|structured_data
            org_upload_dir = get_organization_upload_dir(organization_id)
            file_path = str(org_upload_dir / safe_filename)

            content = await file.read()
            with open(file_path, "wb") as buffer:
                buffer.write(content)
            file_size = len(content)
            vector_store_name = f"doc_{file_id}"
            sqlite_path = None
            org_vector_dir = get_organization_vector_store_dir(organization_id)
            org_structured_dir = get_organization_structured_data_dir(organization_id)

            if file_type in STRUCTURED_FILE_TYPES:
                sqlite_path, documents = process_structured(
                    file_path,
                    file_type,
                    vector_store_name,
                    output_dir=str(org_structured_dir),
                )
                chunk_count = len(documents)
                if chunk_count == 0:
                    if sqlite_path and os.path.exists(sqlite_path):
                        os.remove(sqlite_path)
                    os.remove(file_path)
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Structured file could not be processed or is empty",
                    )
                vector_store_path = self.vector_store_manager.create_vector_store(
                    documents,
                    vector_store_name,
                    base_dir=str(org_vector_dir),
                )
            else:
                documents = self.document_processor.process_document(file_path, file_type)
                chunk_count = len(documents)
                if chunk_count == 0:
                    os.remove(file_path)
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Document could not be processed or is empty",
                    )
                vector_store_path = self.vector_store_manager.create_vector_store(
                    documents,
                    vector_store_name,
                    base_dir=str(org_vector_dir),
                )

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
                "version": 1,
            }
            if sqlite_path is not None:
                document_dict["sqlite_path"] = sqlite_path

            db_document = await self.document_crud.create_from_dict(self.db, obj_dict=document_dict)
            
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
            
            # Provide more user-friendly error messages
            error_message = str(e)
            if "api key" in error_message.lower() or "api_key" in error_message.lower():
                if "expired" in error_message.lower() or "invalid" in error_message.lower():
                    detail = "API key expired or invalid. Please contact the administrator to renew the API keys."
                else:
                    detail = f"API key error: {error_message}"
            elif "vector store" in error_message.lower():
                detail = f"Error creating document embeddings: {error_message}"
            else:
                detail = f"Error processing document: {error_message}"
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=detail
            )
    
    async def list_documents(
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
            return await self.document_crud.get_by_organization(
                self.db,
                organization_id=organization_id,
                category=category,
                user=user
            )

        # Get user's organization documents
        if user.organization_id:
            return await self.document_crud.get_by_organization(
                self.db,
                organization_id=user.organization_id,
                category=category,
                user=user
            )
        
        return []
    
    async def get_document(self, document_id: int, user: User) -> Document:
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
        
        document = await self.document_crud.get(self.db, id=document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        if not self.document_crud.can_access(document, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this document"
            )
        return document

    async def delete_document(self, document_id: int, user: User) -> None:
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
        
        document = await self.document_crud.get(self.db, id=document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
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
            vector_store_path = document.vector_store_path
            file_path = document.file_path
            sqlite_path = getattr(document, "sqlite_path", None)

            await self.document_crud.delete(self.db, id=document_id)

            try:
                if vector_store_path:
                    self.vector_store_manager.delete_vector_store(vector_store_path)
            except Exception as e:
                print(f"Warning: Could not delete vector store at {vector_store_path}: {str(e)}")

            try:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"Warning: Could not delete file at {file_path}: {str(e)}")

            if sqlite_path and os.path.exists(sqlite_path):
                try:
                    os.remove(sqlite_path)
                except Exception as e:
                    print(f"Warning: Could not delete SQLite at {sqlite_path}: {str(e)}")
        
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting document: {str(e)}"
            )
    
    def _validate_file_type(self, file: UploadFile) -> str:
        """
        Validate and determine file type.
        Supported: PDF, DOCX, TXT, HTML, MD, Excel (xlsx/xls), CSV, SQLite (db/sqlite).
        """
        allowed_mime = {
            "application/pdf": "pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
            "text/plain": "txt",
            "text/html": "html",
            "text/csv": "csv",
            "application/vnd.ms-excel": "xls",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
            "application/octet-stream": None,  # infer from extension
        }
        file_type = allowed_mime.get(file.content_type)
        if not file_type:
            filename_lower = (file.filename or "").lower()
            if filename_lower.endswith(".pdf"):
                file_type = "pdf"
            elif filename_lower.endswith((".docx", ".doc")):
                file_type = "docx"
            elif filename_lower.endswith(".txt"):
                file_type = "txt"
            elif filename_lower.endswith((".html", ".htm")):
                file_type = "html"
            elif filename_lower.endswith((".md", ".markdown")):
                file_type = "md"
            elif filename_lower.endswith(".csv"):
                file_type = "csv"
            elif filename_lower.endswith(".xlsx"):
                file_type = "xlsx"
            elif filename_lower.endswith(".xls"):
                file_type = "xls"
            elif filename_lower.endswith((".db", ".sqlite", ".sqlite3")):
                file_type = "db"
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Unsupported file type. Supported: PDF, DOCX, TXT, HTML, MD, Excel (xlsx/xls), CSV, SQLite (db/sqlite)",
                )
        return file_type

